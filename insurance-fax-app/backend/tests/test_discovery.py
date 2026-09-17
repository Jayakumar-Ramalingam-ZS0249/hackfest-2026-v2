import pytest

from app.agents.discovery import AGENT_WHITELIST, classify_domain, run_discovery
from app.core.exceptions import InvalidDocumentError
from app.services.ai.base import AIProvider
from app.services.ai.rule_based_provider import RuleBasedProvider


class _FakeAiProvider(AIProvider):
    name = "fake_ai"
    supports_chat = False

    def __init__(self, response: dict):
        self._response = response

    def extract_fields(self, document_text, field_names):
        return {}

    def generate_json(self, prompt, system_prompt=""):
        return self._response


class _BrokenAiProvider(AIProvider):
    name = "broken"
    supports_chat = False

    def extract_fields(self, document_text, field_names):
        return {}

    def generate_json(self, prompt, system_prompt=""):
        raise RuntimeError("simulated network failure")


HEALTHCARE_PROCESS = (
    "1. Fax received with patient demographics and diagnosis.\n"
    "2. Clinical reviewer checks the diagnosis against policy criteria.\n"
    "3. Prior authorization decision recorded and sent back to the hospital.\n"
)

COLLECTIONS_PROCESS = (
    "1. Account flagged as delinquent after 60 days past due.\n"
    "2. Agent reviews payment plan eligibility.\n"
    "3. Settlement offer sent to the debtor.\n"
)


def test_classify_domain_healthcare():
    assert classify_domain(HEALTHCARE_PROCESS) == "healthcare"


def test_classify_domain_collections():
    assert classify_domain(COLLECTIONS_PROCESS) == "collections"


def test_classify_domain_customer_service():
    text = "Customer submits a support ticket to the help desk about a billing complaint."
    assert classify_domain(text) == "customer_service"


def test_classify_domain_general_fallback():
    assert classify_domain("Employees file expense reports each month.") == "general"


def test_empty_process_text_is_rejected_before_any_ai_call():
    with pytest.raises(InvalidDocumentError):
        run_discovery("   ", RuleBasedProvider())


def test_oversized_process_text_is_rejected():
    huge_text = "a" * 20_001
    with pytest.raises(InvalidDocumentError):
        run_discovery(huge_text, RuleBasedProvider())


def test_healthcare_process_recommends_only_whitelisted_agents_with_no_ai_configured():
    result = run_discovery(HEALTHCARE_PROCESS, RuleBasedProvider())
    assert result["domain"] == "healthcare"
    assert result["assessment_source"] == "rule_based"
    assert set(result["recommended_agents"]).issubset(set(AGENT_WHITELIST["healthcare"]))
    assert "Policy Agent" in result["recommended_agents"]


def test_collections_process_recommends_risk_agent():
    result = run_discovery(COLLECTIONS_PROCESS, RuleBasedProvider())
    assert result["domain"] == "collections"
    assert "Risk Agent" in result["recommended_agents"]


def test_different_processes_produce_different_architectures():
    healthcare_result = run_discovery(HEALTHCARE_PROCESS, RuleBasedProvider())
    collections_result = run_discovery(COLLECTIONS_PROCESS, RuleBasedProvider())
    assert set(healthcare_result["recommended_agents"]) != set(collections_result["recommended_agents"])
    assert healthcare_result["domain"] != collections_result["domain"]


def test_out_of_whitelist_agent_from_mocked_ai_is_filtered_not_trusted():
    fake_response = {
        "process_name": "Prior Auth",
        "human_actors": 3,
        "manual_touchpoints": 4,
        "agent_suitability_score": 80,
        "recommended_agents": ["Clinical Agent", "Rogue Hallucinated Agent"],
        "current_state": "Manual.",
        "future_state": "Automated.",
        "roadmap": ["Step 1"],
    }
    result = run_discovery(HEALTHCARE_PROCESS, _FakeAiProvider(fake_response))
    assert "Rogue Hallucinated Agent" not in result["recommended_agents"]
    assert "Rogue Hallucinated Agent" in result["rejected_agents"]
    assert "Clinical Agent" in result["recommended_agents"]
    assert all(agent in AGENT_WHITELIST["healthcare"] for agent in result["recommended_agents"])


def test_ai_call_failure_falls_back_to_rule_based_assessment():
    result = run_discovery(HEALTHCARE_PROCESS, _BrokenAiProvider())
    assert result["assessment_source"] == "rule_based"
    assert result["recommended_agents"]


def test_fallback_assessment_varies_with_input_not_a_flat_constant():
    # Regression guard: the rule-based fallback previously returned
    # human_actors=1 / manual_touchpoints=1 / agent_suitability_score=55 for
    # almost any input (a single-paragraph paste has no real line breaks),
    # making the tool look static/canned whenever the AI was unavailable.
    short_result = run_discovery("Employee files an expense report.", RuleBasedProvider())
    long_result = run_discovery(
        "1. Fax received with patient demographics and diagnosis. "
        "2. Clinical reviewer checks the diagnosis against policy criteria. "
        "3. Policy agent verifies coverage and records the decision. "
        "4. Workflow agent sends the approval notice back to the hospital.",
        RuleBasedProvider(),
    )
    assert long_result["manual_touchpoints"] > short_result["manual_touchpoints"]
    assert long_result["agent_suitability_score"] != short_result["agent_suitability_score"]
    assert long_result["manual_touchpoints"] > 1  # pasted-as-one-line input still splits into real steps
