"""The single source of truth for turning tool outputs into a recommendation and
an approved amount. This module is pure, deterministic Python — the AI never
calls it and never produces its own version of this logic. Both the
Claude-orchestrated path and the rule-based fallback path funnel through this
exact function (app.agent.pipeline), so the outcome only ever depends on the
tool outputs gathered, never on which engine gathered them.
"""

from typing import Any, Dict, Optional, TypedDict


class Decision(TypedDict):
    recommendation: str
    approved_amount: Optional[float]
    primary_reason: str


def derive_decision(tool_outputs: Dict[str, Dict[str, Any]]) -> Decision:
    identity = tool_outputs.get("verify_identity", {})
    fraud = tool_outputs.get("check_fraud_flags", {})
    compliance = tool_outputs.get("check_policy_compliance", {})
    risk_calc = tool_outputs.get("calculate_risk_adjusted_amount", {})

    if not identity.get("aadhar_valid") or not identity.get("pan_valid"):
        return {
            "recommendation": "reject",
            "approved_amount": None,
            "primary_reason": "identity_verification_failed",
        }

    if fraud.get("flagged"):
        return {
            "recommendation": "escalate",
            "approved_amount": None,
            "primary_reason": "fraud_flag",
        }

    if not compliance.get("compliant", True):
        return {
            "recommendation": "escalate",
            "approved_amount": None,
            "primary_reason": "policy_non_compliance",
        }

    approved_amount = risk_calc.get("approved_amount")
    if approved_amount is None:
        return {
            "recommendation": "escalate",
            "approved_amount": None,
            "primary_reason": "incomplete_calculation",
        }

    return {
        "recommendation": "approve",
        "approved_amount": approved_amount,
        "primary_reason": "standard_approval",
    }
