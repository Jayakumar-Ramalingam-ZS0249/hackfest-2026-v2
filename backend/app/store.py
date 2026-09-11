"""In-memory data store for the demo. A real deployment would swap this module
for a database-backed repository; every other module only talks to the store
through these functions, so that swap would not touch tools, agent, or routes.
"""

import itertools
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.mock_data.seed import build_seed_applicants
from app.models.schemas import Applicant, ToolCallRecord, AIRecommendation

_lock = threading.Lock()

_applicants: Dict[str, Applicant] = {a.applicant_id: a for a in build_seed_applicants()}
_audit_log: List[ToolCallRecord] = []
_audit_id_counter = itertools.count(1)

_SORTABLE_FIELDS = {
    "risk_score",
    "claim_amount_requested",
    "policy_tenure_years",
    "prior_claims_count",
    "last_updated",
    "submitted_at",
    "name",
}


def list_applicants(
    status: Optional[str] = None,
    sort_by: Optional[str] = None,
    order: str = "asc",
) -> List[Applicant]:
    items = list(_applicants.values())
    if status:
        items = [a for a in items if a.status == status]
    if sort_by in _SORTABLE_FIELDS:
        items.sort(key=lambda a: getattr(a, sort_by), reverse=(order == "desc"))
    else:
        items.sort(key=lambda a: a.applicant_id)
    return items


def get_applicant(applicant_id: str) -> Optional[Applicant]:
    return _applicants.get(applicant_id)


def require_applicant(applicant_id: str) -> Applicant:
    applicant = get_applicant(applicant_id)
    if applicant is None:
        raise KeyError(f"Unknown applicant_id: {applicant_id}")
    return applicant


def next_audit_id() -> int:
    with _lock:
        return next(_audit_id_counter)


def append_audit(record: ToolCallRecord) -> None:
    with _lock:
        _audit_log.append(record)


def list_audit(applicant_id: Optional[str] = None) -> List[ToolCallRecord]:
    items = _audit_log
    if applicant_id:
        items = [r for r in items if r.applicant_id == applicant_id]
    return sorted(items, key=lambda r: r.timestamp)


def get_audit_since(applicant_id: str, since: datetime) -> List[ToolCallRecord]:
    return [
        record
        for record in _audit_log
        if record.applicant_id == applicant_id and record.timestamp >= since
    ]


def set_ai_recommendation(applicant_id: str, recommendation: AIRecommendation) -> Applicant:
    with _lock:
        applicant = require_applicant(applicant_id)
        applicant.ai_recommendation = recommendation
        applicant.last_updated = datetime.now(timezone.utc)
        return applicant


def apply_decision(
    applicant_id: str,
    decision: str,
    decided_by: str,
    notes: Optional[str],
    override_amount: Optional[float],
) -> Applicant:
    """The only function in the entire app that may set status to 'approved' or
    'rejected' — it is only ever called from the human-submitted decision
    endpoint, never from the AI review pipeline."""
    with _lock:
        applicant = require_applicant(applicant_id)

        if decision == "approved":
            applicant.status = "approved"
            if override_amount is not None:
                applicant.approved_amount = override_amount
            elif applicant.ai_recommendation and applicant.ai_recommendation.approved_amount is not None:
                applicant.approved_amount = applicant.ai_recommendation.approved_amount
            else:
                applicant.approved_amount = applicant.claim_amount_requested
        elif decision == "rejected":
            applicant.status = "rejected"
            applicant.approved_amount = None
        elif decision == "more_info":
            applicant.status = "needs_human_review"
        else:
            raise ValueError(f"Unknown decision: {decision}")

        applicant.decided_by = decided_by
        applicant.decision_notes = notes
        applicant.last_updated = datetime.now(timezone.utc)

        audit_id = next(_audit_id_counter)
        _audit_log.append(
            ToolCallRecord(
                id=audit_id,
                applicant_id=applicant_id,
                tool_name="human_decision",
                timestamp=applicant.last_updated,
                inputs={"decision": decision, "decided_by": decided_by, "notes": notes or ""},
                outputs={"status": applicant.status, "approved_amount": applicant.approved_amount},
            )
        )
        return applicant


def dashboard_summary() -> dict:
    items = list(_applicants.values())
    today = datetime.now(timezone.utc).date()

    approved_today = [a for a in items if a.status == "approved" and a.last_updated.date() == today]
    rejected_today = [a for a in items if a.status == "rejected" and a.last_updated.date() == today]
    decided = [a for a in items if a.status in ("approved", "rejected")]

    processing_minutes = [
        (a.last_updated - a.submitted_at).total_seconds() / 60.0 for a in decided
    ]
    avg_processing_time_minutes = (
        round(sum(processing_minutes) / len(processing_minutes), 1) if processing_minutes else 0.0
    )

    claims_by_status: Dict[str, int] = {}
    for a in items:
        claims_by_status[a.status] = claims_by_status.get(a.status, 0) + 1

    return {
        "total_applications": len(items),
        "total_pending": sum(1 for a in items if a.status in ("pending_review", "needs_human_review")),
        "total_approved_today": len(approved_today),
        "total_rejected_today": len(rejected_today),
        "avg_processing_time_minutes": avg_processing_time_minutes,
        "total_value_approved": sum(a.approved_amount or 0 for a in items if a.status == "approved"),
        "claims_by_status": claims_by_status,
    }
