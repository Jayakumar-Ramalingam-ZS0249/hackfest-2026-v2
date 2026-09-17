from app.agents.implementation import LOW_CONFIDENCE_ESCALATION_THRESHOLD, run_agent_simulation
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


class _ShouldNotBeCalledProvider(AIProvider):
    name = "should_not_be_called"
    supports_chat = False

    def extract_fields(self, document_text, field_names):
        return {}

    def generate_json(self, prompt, system_prompt=""):
        raise AssertionError("The AI must not be called when confidence is already too low.")


def _field(value):
    return {"value": value, "confidence": 0.9 if value else 0.0}


def _make_fax_record(*, patient_name="Raj Kumar", diagnosis="Acute pancreatitis", overall_confidence=90):
    return {
        "id": "abc123",
        "fields": {
            "patientName": _field(patient_name),
            "diagnosis": _field(diagnosis),
            "hospitalName": _field("City General Hospital"),
        },
        "overall_confidence": overall_confidence,
    }


def test_low_confidence_forces_escalation_and_skips_ai_call():
    record = _make_fax_record(overall_confidence=LOW_CONFIDENCE_ESCALATION_THRESHOLD - 1)
    result = run_agent_simulation(record, ["Clinical Agent"], _ShouldNotBeCalledProvider())
    assert result["final_status"] == "Escalate to Human Review"
    assert result["skipped_ai_call"] is True
    assert result["policy_agent"]["exception_flagged"] is True


def test_missing_diagnosis_flags_policy_exception_even_if_ai_disagrees():
    record = _make_fax_record(diagnosis=None)
    fake_response = {
        "agents": [{"name": "Clinical Agent", "output": "Looks fine", "reasoning": "No issues found."}],
        "policy_agent": {"exception_flagged": False, "reason": "", "reasoning": "Everything checks out."},
        "final_status": "Auto-Approved",
    }
    result = run_agent_simulation(record, ["Clinical Agent", "Policy Agent"], _FakeAiProvider(fake_response))
    assert result["policy_agent"]["exception_flagged"] is True
    assert result["policy_agent"]["reason"] == "No diagnosis found in document"


def test_missing_patient_name_forces_human_review_even_if_ai_says_auto_approved():
    record = _make_fax_record(patient_name=None)
    fake_response = {
        "agents": [{"name": "Document Intake Agent", "output": "Processed", "reasoning": "All fields present."}],
        "policy_agent": {"exception_flagged": False, "reason": "", "reasoning": "No issues."},
        "final_status": "Auto-Approved",
    }
    result = run_agent_simulation(record, ["Document Intake Agent"], _FakeAiProvider(fake_response))
    assert result["final_status"] == "Human Review Required"


def test_valid_record_with_ai_configured_uses_ai_drafted_output():
    record = _make_fax_record()
    fake_response = {
        "agents": [
            {"name": "Clinical Agent", "output": "Diagnosis matches policy criteria.", "reasoning": "Diagnosis code is covered."}
        ],
        "policy_agent": {"exception_flagged": False, "reason": "", "reasoning": "No exceptions found."},
        "final_status": "Auto-Approved",
    }
    result = run_agent_simulation(record, ["Clinical Agent"], _FakeAiProvider(fake_response))
    assert result["final_status"] == "Auto-Approved"
    assert result["policy_agent"]["exception_flagged"] is False
    assert result["reasoning_per_agent"]["Clinical Agent"] == "Diagnosis code is covered."


def test_rule_based_provider_gives_deterministic_placeholder_without_ai():
    record = _make_fax_record()
    result = run_agent_simulation(record, ["Clinical Agent"], RuleBasedProvider())
    assert result["skipped_ai_call"] is False
    assert result["agents"][0]["name"] == "Clinical Agent"
