import unittest

from app.services.ai.rule_based_provider import RuleBasedProvider
from app.services.extraction.claim_extraction_service import CANONICAL_FIELDS, ClaimExtractionService


class ClaimExtractionServiceTests(unittest.TestCase):
    def test_extracts_known_fields_with_verified_status(self):
        text = "Patient Name: Raj Kumar\nDate of Birth: 12/03/1985\nHospital Name: City General Hospital\n"
        result = ClaimExtractionService.extract(
            pages=[text], full_text=text, ai_provider=RuleBasedProvider(), low_confidence_threshold=0.70
        )
        patient = result.fields["patientName"]
        self.assertEqual(patient.value, "Raj Kumar")
        self.assertEqual(patient.verification_status, "VERIFIED")
        self.assertIn(patient.status, ("verified", "review_required"))

    def test_missing_field_is_not_found_with_zero_confidence(self):
        text = "This document only mentions a hospital name and nothing else about the patient."
        result = ClaimExtractionService.extract(
            pages=[text], full_text=text, ai_provider=RuleBasedProvider(), low_confidence_threshold=0.70
        )
        member_id = result.fields["memberId"]
        self.assertIsNone(member_id.value)
        self.assertEqual(member_id.status, "not_found")
        self.assertEqual(member_id.confidence, 0.0)

    def test_conflicting_values_across_pages_are_flagged(self):
        page1 = "Date of Birth: 12/03/1985\nPatient Name: Raj Kumar\n"
        page2 = "Date of Birth: 13/03/1985\n"
        full_text = page1 + "\n" + page2
        result = ClaimExtractionService.extract(
            pages=[page1, page2], full_text=full_text, ai_provider=RuleBasedProvider(), low_confidence_threshold=0.70
        )
        dob = result.fields["dateOfBirth"]
        self.assertEqual(dob.status, "conflict")
        self.assertEqual(len(dob.conflicts), 2)
        candidate_pages = {c.page for c in dob.conflicts}
        self.assertEqual(candidate_pages, {1, 2})

    def test_all_canonical_fields_are_always_present_in_result(self):
        result = ClaimExtractionService.extract(pages=[""], full_text="", ai_provider=RuleBasedProvider(), low_confidence_threshold=0.70)
        self.assertEqual(set(result.fields.keys()), set(CANONICAL_FIELDS))


if __name__ == "__main__":
    unittest.main()
