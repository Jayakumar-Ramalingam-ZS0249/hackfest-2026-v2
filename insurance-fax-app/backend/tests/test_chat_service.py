import unittest

from app.services.ai.base import AIProvider
from app.services.ai.rule_based_provider import RuleBasedProvider
from app.services.chat.chat_service import AI_UNAVAILABLE_MESSAGE, NOT_FOUND_MESSAGE, ChatService
from app.services.extraction.claim_extraction_service import ClaimExtractionService


class _AlwaysFailingAiProvider(AIProvider):
    """Simulates a real-world AI outage/quota exhaustion -- chat() always raises."""

    name = "flaky_ai"
    supports_chat = True

    def extract_fields(self, document_text, field_names):
        return {}

    def chat(self, question, context, system_prompt):
        raise RuntimeError("ResourceExhausted: quota exceeded")


def _fields_from(text: str):
    result = ClaimExtractionService.extract(pages=[text], full_text=text, ai_provider=RuleBasedProvider(), low_confidence_threshold=0.70)
    return result.fields


class ChatServiceTests(unittest.TestCase):
    def setUp(self):
        self.text = (
            "Patient Name: Raj Kumar\nHospital Name: City General Hospital\n"
            "Diagnosis: Acute pancreatitis\nTotal Claim Amount: Rs. 85000\n"
            "Hospital Bill: Rs. 90000\nApproved Amount: Rs. 80000\n"
        )
        self.fields = _fields_from(self.text)

    def test_quick_action_summarize_uses_only_extracted_data(self):
        answer, sources, options = ChatService.ask(
            "Summarize this claim", self.fields, pages=[self.text], full_text=self.text, ai_provider=RuleBasedProvider()
        )
        self.assertIn("Raj Kumar", answer)
        self.assertIn("City General Hospital", answer)
        self.assertEqual(options, [])

    def test_quick_action_missing_information(self):
        answer, _, _ = ChatService.ask(
            "What information is missing?", self.fields, pages=[self.text], full_text=self.text, ai_provider=RuleBasedProvider()
        )
        self.assertIn("Member ID", answer)

    def test_freeform_question_without_ai_provider_is_graceful_not_hallucinated(self):
        answer, sources, options = ChatService.ask(
            "What is the patient's father's name?", self.fields, pages=[self.text], full_text=self.text, ai_provider=RuleBasedProvider()
        )
        # No AI provider is configured (rule-based has supports_chat=False), so the
        # service must say so rather than inventing an answer.
        self.assertNotIn("father", answer.lower())
        self.assertEqual(sources, [])
        self.assertEqual(options, [])

    def test_ambiguous_generic_amount_question_asks_for_clarification(self):
        answer, sources, options = ChatService.ask(
            "What is the amount he is asking?", self.fields, pages=[self.text], full_text=self.text, ai_provider=RuleBasedProvider()
        )
        self.assertIn("multiple possible matches", answer.lower())
        self.assertGreater(len(options), 1)
        self.assertIn("Claim Amount", options)

    def test_specific_amount_question_is_not_treated_as_ambiguous(self):
        # "claim amount" is specific enough to skip clarification, even though it
        # contains the generic trigger word "amount".
        _answer, _sources, options = ChatService.ask(
            "What is the claim amount?", self.fields, pages=[self.text], full_text=self.text, ai_provider=RuleBasedProvider()
        )
        self.assertEqual(options, [])

    def test_no_fabrication_message_constant_does_not_invent_names(self):
        self.assertNotIn("Priya", NOT_FOUND_MESSAGE)

    def test_direct_field_questions_are_answered_without_any_ai_call(self):
        # These are exactly the quick-action chips the UI suggests -- they must
        # be answered straight from extracted fields even when no AI provider
        # is configured at all (RuleBasedProvider.supports_chat is False), so
        # they can never depend on an external AI call succeeding.
        cases = {
            "What is the claim amount?": "85000",
            "What hospital treated the patient?": "City General Hospital",
            "What is the patient's name?": "Raj Kumar",
            "What is the Deductible Amount?": None,  # not present in setUp's text
        }
        for question, expected_substring in cases.items():
            answer, sources, options = ChatService.ask(
                question, self.fields, pages=[self.text], full_text=self.text, ai_provider=RuleBasedProvider()
            )
            self.assertEqual(options, [])
            if expected_substring:
                self.assertIn(expected_substring, answer)
                self.assertEqual(len(sources), 1)
            else:
                self.assertIn("was not found", answer)

    def test_ai_outage_gives_an_honest_unavailable_message_not_a_generic_apology(self):
        # A question with no direct-field match and no AI available should
        # explain the AI is unreachable -- not silently claim the information
        # itself is unverifiable, which would mislead a manager into doubting
        # good extracted data during a transient outage/quota issue.
        answer, sources, options = ChatService.ask(
            "Does this claim look suspicious to you?",
            self.fields,
            pages=[self.text],
            full_text=self.text,
            ai_provider=_AlwaysFailingAiProvider(),
        )
        self.assertEqual(answer, AI_UNAVAILABLE_MESSAGE)
        self.assertEqual(sources, [])
        self.assertEqual(options, [])


if __name__ == "__main__":
    unittest.main()
