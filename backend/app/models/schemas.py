"""Pydantic data models shared across the app. These are the single source of
truth for the JSON shapes returned by the API — the Angular frontend's
TypeScript interfaces mirror these field-for-field.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ClaimStatus = Literal["pending_review", "approved", "rejected", "needs_human_review"]

ClaimType = Literal[
    "Hospitalization",
    "Surgery",
    "Outpatient",
    "Critical Illness",
    "Maternity",
    "Accident",
]

RecommendationAction = Literal["approve", "reject", "escalate"]

DecisionAction = Literal["approved", "rejected", "more_info"]

AIEngine = Literal["claude", "fallback_rules"]


class ToolCallRecord(BaseModel):
    """One provenance-tagged tool invocation, used for the audit-log page and
    the applicant detail provenance strip."""

    id: int
    applicant_id: str
    tool_name: str
    timestamp: datetime
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)


class AIRecommendation(BaseModel):
    """The result of one AI-orchestrated review run. The recommendation and
    approved_amount are always derived from tool_calls by deterministic Python
    logic (app.agent.decision_rules) — never invented by the model."""

    applicant_id: str
    recommendation: RecommendationAction
    approved_amount: Optional[float] = None
    rationale: str
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    generated_at: datetime
    engine: AIEngine


class Applicant(BaseModel):
    applicant_id: str
    name: str
    aadhar_number: str
    aadhar_verified: bool
    pan_number: str
    pan_verified: bool
    claim_type: ClaimType
    claim_amount_requested: float
    policy_tenure_years: int
    prior_claims_count: int
    risk_score: float = Field(ge=0.0, le=1.0)
    status: ClaimStatus
    approved_amount: Optional[float] = None
    ai_recommendation: Optional[AIRecommendation] = None
    submitted_at: datetime
    last_updated: datetime
    decided_by: Optional[str] = None
    decision_notes: Optional[str] = None


class DecisionRequest(BaseModel):
    """Body for POST /api/applications/{id}/decision — the one and only place a
    claim's status can move to approved or rejected. Nothing about the AI
    review pipeline can set these statuses on its own."""

    decision: DecisionAction
    decided_by: str = Field(min_length=1, description="Name or email of the human reviewer")
    notes: Optional[str] = None
    override_amount: Optional[float] = Field(
        default=None,
        description=(
            "Optional amount override if the reviewer adjusts the AI-recommended "
            "figure before approving. Ignored for rejected/more_info decisions."
        ),
    )


class DashboardSummary(BaseModel):
    total_applications: int
    total_pending: int
    total_approved_today: int
    total_rejected_today: int
    avg_processing_time_minutes: float
    total_value_approved: float
    claims_by_status: Dict[str, int]
