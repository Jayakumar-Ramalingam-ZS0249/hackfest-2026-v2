"""Ties the planner, the deterministic decision rules, and the rationale
writer together into a single AI review run. This is the only entry point
main.py calls for POST /api/applications/{id}/ai-review.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from app import config, store
from app.agent import decision_rules, planner, rationale
from app.models.schemas import AIRecommendation
from app.tools.registry import TOOL_FUNCTIONS

logger = logging.getLogger(__name__)

REQUIRED_TOOLS = [
    "verify_identity",
    "check_fraud_flags",
    "check_policy_compliance",
    "calculate_risk_adjusted_amount",
]


def _ensure_complete(
    applicant_id: str,
    tool_outputs: Dict[str, Dict[str, Any]],
    call_order: List[str],
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Fills in any required tool that has not been called yet, so the decision
    rules always have a complete picture. Called with empty starting state,
    this function alone *is* the rule-based fallback engine: it runs the same
    four tools in the same fixed order every time.
    """
    identity = tool_outputs.get("verify_identity")
    identity_ok = bool(identity and identity.get("aadhar_valid") and identity.get("pan_valid"))

    for name in REQUIRED_TOOLS:
        if name in tool_outputs:
            continue
        if name == "calculate_risk_adjusted_amount" and identity is not None and not identity_ok:
            # Mirrors the planner's own guidance: don't price a claim attached
            # to an identity that already failed verification.
            continue
        tool_outputs[name] = TOOL_FUNCTIONS[name](applicant_id=applicant_id)
        call_order.append(name)

    return tool_outputs, call_order


def run_ai_review(applicant_id: str) -> AIRecommendation:
    applicant = store.require_applicant(applicant_id)
    run_started_at = datetime.now(timezone.utc)

    tool_outputs: Dict[str, Dict[str, Any]] = {}
    call_order: List[str] = []
    engine = "claude"

    if not config.ANTHROPIC_API_KEY:
        logger.info(
            "ANTHROPIC_API_KEY not configured; using rule-based orchestration for %s", applicant_id
        )
        engine = "fallback_rules"
    else:
        try:
            tool_outputs, call_order = planner.run_planner(applicant_id)
        except Exception:
            logger.exception(
                "Claude planner failed for %s; falling back to rule-based orchestration", applicant_id
            )
            engine = "fallback_rules"
            tool_outputs, call_order = {}, []

    tool_outputs, call_order = _ensure_complete(applicant_id, tool_outputs, call_order)
    decision = decision_rules.derive_decision(tool_outputs)

    rationale_text = None
    if engine == "claude":
        try:
            rationale_text = rationale.write_rationale(applicant, decision, tool_outputs)
        except Exception:
            logger.exception(
                "Rationale writer failed for %s; using templated rationale instead", applicant_id
            )
            engine = "fallback_rules"

    if rationale_text is None:
        rationale_text = rationale.fallback_rationale(applicant, decision, tool_outputs)

    tool_call_records = store.get_audit_since(applicant_id, run_started_at)

    recommendation = AIRecommendation(
        applicant_id=applicant_id,
        recommendation=decision["recommendation"],
        approved_amount=decision["approved_amount"],
        rationale=rationale_text,
        tool_calls=tool_call_records,
        generated_at=datetime.now(timezone.utc),
        engine=engine,
    )
    store.set_ai_recommendation(applicant_id, recommendation)
    return recommendation
