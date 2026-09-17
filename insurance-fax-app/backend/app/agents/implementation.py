"""
Agent simulation.

Takes an ALREADY-EXTRACTED claim record -- the exact output of
agents/orchestrator.py's run_pipeline(), never a second OCR/extraction
pass -- plus a Discovery-recommended agent list, and simulates what
each agent would output.

Same rule as eligibility.py's threshold logic: every compliance-relevant
decision (exception flags, human-review escalation) is enforced here in
code and can override whatever the LLM returns. The model drafts; code
decides.
"""

import logging

from ..services.ai.base import AIProvider

logger = logging.getLogger("app.agents.implementation")

# 0-100 scale, matches claim_record["overall_confidence"] from orchestrator.py.
LOW_CONFIDENCE_ESCALATION_THRESHOLD = 60

SIMULATION_PROMPT = """You are simulating a team of automation agents processing an
insurance claim. The agents available are: {agents}.

Extracted claim fields (already verified against the source document -- treat as ground truth):
{fields_summary}

For each agent, draft a plausible one-line output and a one-sentence "reasoning" explaining
why it reached that conclusion. Also propose a final_status, one of:
"Auto-Approved", "Human Review Required", "Escalate to Human Review".

Return ONLY valid JSON with this exact shape, no extra commentary:
{{
  "agents": [{{"name": "<agent name>", "output": "<one line>", "reasoning": "<one sentence>"}}],
  "policy_agent": {{"exception_flagged": <true or false>, "reason": "<short reason or empty string>", "reasoning": "<one sentence>"}},
  "final_status": "<Auto-Approved|Human Review Required|Escalate to Human Review>"
}}
"""


def _field_value(record: dict, name: str) -> str | None:
    return record.get("fields", {}).get(name, {}).get("value")


def _fields_summary(record: dict) -> str:
    lines = [f"- {name}: {field.get('value') or 'NOT FOUND'}" for name, field in record.get("fields", {}).items()]
    return "\n".join(lines) if lines else "(no fields extracted)"


def _fallback_simulation(agents: list[str], reason: str) -> dict:
    # `reason` already says precisely why (not configured vs. call failed) --
    # reuse it verbatim in the output too, instead of a separate hardcoded
    # phrase that could contradict it (e.g. claiming "not configured" when
    # the provider is configured but the call itself failed).
    return {
        "agents": [{"name": agent, "output": f"Not available — {reason}", "reasoning": reason} for agent in agents],
        "policy_agent": {"exception_flagged": False, "reason": "", "reasoning": reason},
        "final_status": "Human Review Required",
    }


def run_agent_simulation(fax_record: dict, recommended_agents: list[str], ai_provider: AIProvider) -> dict:
    has_patient_name = bool((_field_value(fax_record, "patientName") or "").strip())
    has_diagnosis = bool((_field_value(fax_record, "diagnosis") or "").strip())
    overall_confidence = fax_record.get("overall_confidence") or 0

    # --- Low confidence: escalate and skip the LLM call entirely (saves cost;
    # matches eligibility.py's "don't trust low-confidence data" principle). ---
    if overall_confidence < LOW_CONFIDENCE_ESCALATION_THRESHOLD:
        reason = (
            f"Overall extraction confidence ({overall_confidence}%) is below the required "
            f"threshold ({LOW_CONFIDENCE_ESCALATION_THRESHOLD}%)."
        )
        return {
            "agents": [],
            "policy_agent": {"exception_flagged": True, "reason": "Low extraction confidence", "reasoning": reason},
            "final_status": "Escalate to Human Review",
            "skipped_ai_call": True,
            "reasoning_per_agent": {},
        }

    if ai_provider.name == "rule_based":
        result = _fallback_simulation(recommended_agents, "AI provider is not configured; showing a deterministic placeholder.")
    else:
        prompt = SIMULATION_PROMPT.format(agents=", ".join(recommended_agents), fields_summary=_fields_summary(fax_record))
        try:
            result = ai_provider.generate_json(prompt)
        except Exception as exc:
            logger.warning("simulation_ai_call_failed: %s", exc)
            result = _fallback_simulation(recommended_agents, "The AI provider could not be reached.")

    # --- Code-level overrides: never trust the LLM alone for these. ---
    policy_agent = result.get("policy_agent") or {}
    if not has_diagnosis:
        policy_agent = {
            "exception_flagged": True,
            "reason": "No diagnosis found in document",
            "reasoning": policy_agent.get("reasoning") or "The diagnosis field was not present in the extracted document.",
        }
    result["policy_agent"] = policy_agent

    final_status = result.get("final_status") or "Human Review Required"
    if not has_patient_name:
        final_status = "Human Review Required"
    result["final_status"] = final_status

    result["skipped_ai_call"] = False
    result["reasoning_per_agent"] = {a.get("name"): a.get("reasoning") for a in result.get("agents", []) if a.get("name")}
    return result
