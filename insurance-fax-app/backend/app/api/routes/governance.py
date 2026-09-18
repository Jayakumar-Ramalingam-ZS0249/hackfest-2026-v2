"""
Agent governance policy.

Exposes the real confidence/match-score thresholds that the extraction
pipeline (agents/orchestrator.py) actually enforces to decide whether a
claim is auto-decided by the agents or routed to a human. This is a
read view onto core.config.Settings, not a separate/duplicated policy
store -- change the underlying env vars and this reflects it.
"""

from fastapi import APIRouter

from ...core.config import get_settings

router = APIRouter(tags=["governance"])


@router.get("/governance/policy")
def get_governance_policy():
    settings = get_settings()
    return {
        "invalidMatchThreshold": settings.invalid_match_threshold,
        "reviewMatchThreshold": settings.review_match_threshold,
        "lowConfidenceThreshold": settings.low_confidence_threshold,
        "aiProvider": settings.ai_provider,
        "aiConfigured": settings.ai_configured,
    }
