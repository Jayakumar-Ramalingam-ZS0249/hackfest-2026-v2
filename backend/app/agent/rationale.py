"""The rationale writer: a separate Claude call that turns already-computed
tool outputs and an already-decided recommendation into a short plain-English
explanation for a compliance reviewer. This call cannot change the
recommendation or the amount — it can only describe numbers that already
exist, and a deterministic templated fallback (fallback_rationale) produces an
equivalent explanation if Claude is unavailable.
"""

import json
import logging
from typing import Any, Dict

import anthropic

from app import config
from app.agent.decision_rules import Decision
from app.models.schemas import Applicant

logger = logging.getLogger(__name__)

RATIONALE_SYSTEM_PROMPT = """You are a compliance-facing writing assistant for an insurance \
claims operations team. You will be given the factual outputs of an automated claims-review \
pipeline — identity verification, fraud checks, policy compliance, and (when relevant) a \
risk-adjusted amount calculation — plus the final recommendation that a separate deterministic \
process already made from those outputs. Write a 2-4 sentence plain-English rationale for a \
human compliance reviewer, in the tone of an underwriting note. State the recommended action \
(and amount, if any) and explain the key factors driving it, using ONLY the figures provided to \
you. Never introduce a number, percentage, or figure that was not given to you. Do not use \
markdown formatting — return plain prose only."""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _facts_payload(applicant: Applicant, decision: Decision, tool_outputs: Dict[str, Dict[str, Any]]) -> str:
    return json.dumps(
        {
            "applicant_name": applicant.name,
            "claim_type": applicant.claim_type,
            "claim_amount_requested": applicant.claim_amount_requested,
            "policy_tenure_years": applicant.policy_tenure_years,
            "prior_claims_count": applicant.prior_claims_count,
            "risk_score": applicant.risk_score,
            "recommendation": decision["recommendation"],
            "approved_amount": decision["approved_amount"],
            "tool_outputs": tool_outputs,
        },
        default=str,
    )


def write_rationale(applicant: Applicant, decision: Decision, tool_outputs: Dict[str, Dict[str, Any]]) -> str:
    client = _client()
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=300,
        system=RATIONALE_SYSTEM_PROMPT,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": _facts_payload(applicant, decision, tool_outputs)}],
    )
    text = " ".join(block.text.strip() for block in response.content if block.type == "text" and block.text.strip())
    if not text:
        raise ValueError("Claude returned no usable text for the rationale")
    return text


def fallback_rationale(applicant: Applicant, decision: Decision, tool_outputs: Dict[str, Dict[str, Any]]) -> str:
    """Deterministic templated rationale used when the Claude call is
    unavailable or fails. Mirrors the tone and level of detail of the
    AI-written version so the demo experience is consistent either way."""
    recommendation = decision["recommendation"]
    amount = decision["approved_amount"]

    if recommendation == "reject":
        identity = tool_outputs.get("verify_identity", {})
        failed = []
        if not identity.get("aadhar_valid"):
            failed.append("Aadhar")
        if not identity.get("pan_valid"):
            failed.append("PAN")
        docs = " and ".join(failed) if failed else "identity"
        return (
            f"This claim is recommended for rejection because {docs} verification did not pass "
            f"against the system of record. No amount can be approved until identity verification "
            f"is completed successfully; the applicant should be asked to resubmit valid documents."
        )

    if recommendation == "escalate":
        reasons = []
        fraud = tool_outputs.get("check_fraud_flags", {})
        compliance = tool_outputs.get("check_policy_compliance", {})
        if fraud.get("flagged"):
            reasons.extend(fraud.get("reasons", []))
        if not compliance.get("compliant", True):
            reasons.append(compliance.get("reason", "a policy compliance issue"))
        reason_text = "; ".join(reasons) if reasons else "one or more automated checks could not be cleared"
        return (
            f"This claim is escalated for human review because {reason_text}. A final decision "
            f"requires manual underwriting judgment before any amount can be approved."
        )

    # approve
    calc = tool_outputs.get("calculate_risk_adjusted_amount", {})
    requested = applicant.claim_amount_requested
    reduced = amount is not None and amount < requested
    factors = []
    if calc.get("risk_penalty", 0) > 0:
        factors.append(f"a risk score of {applicant.risk_score:.2f}")
    if calc.get("prior_claims_penalty", 0) > 0:
        factors.append(f"{applicant.prior_claims_count} prior claim(s) on record")
    if calc.get("tenure_bonus", 0) > 0:
        factors.append(f"a {applicant.policy_tenure_years}-year policy tenure")
    factor_text = " and ".join(factors) if factors else "the applicant's overall risk profile"

    if reduced:
        return (
            f"This claim is recommended for approval at ₹{amount:,.0f} (reduced from the "
            f"₹{requested:,.0f} requested) because {factor_text} supports partial approval under "
            f"standard guidelines. The reduction reflects the automated risk adjustment applied to "
            f"this profile, not a rejection of the claim."
        )
    return (
        f"This claim is recommended for approval at the full requested amount of ₹{amount:,.0f} "
        f"because {factor_text} places it within standard guidelines with no risk-based reduction "
        f"required."
    )
