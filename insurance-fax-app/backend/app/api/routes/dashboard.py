"""
Dashboard statistics and analytics.

/dashboard/statistics is the original lightweight endpoint the sidebar
badges use -- kept unchanged. /dashboard/overview is the new, richer
endpoint the redesigned dashboard page consumes: it accepts real
server-side filters and returns everything computed from the actual
claim/audit store (see analytics_service.py) -- nothing here is
fabricated. /dashboard/export streams a CSV of the same filtered set.
"""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from ...core.config import get_settings
from ...core.exceptions import AppError
from ...repositories.claim_repository import claim_repository
from ...services.dashboard.analytics_service import build_attention_summary, build_export_rows, build_overview

router = APIRouter(tags=["dashboard"])


def _parse_date_param(value: str | None, *, end_of_day: bool = False, param_name: str = "date") -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise AppError(
            f"'{param_name}' must be an ISO date (YYYY-MM-DD).", code="INVALID_DATE", status_code=400
        ) from exc
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt


@router.get("/dashboard/statistics")
def get_dashboard_statistics():
    return claim_repository.statistics()


@router.get("/dashboard/overview")
def get_dashboard_overview(
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    status: str = Query("all"),
    confidence: str = Query("all"),
    insurance: str = Query("all"),
):
    settings = get_settings()
    claims = claim_repository.list_all(include_deleted=False)
    audit_log = claim_repository.list_audit_log()
    data = build_overview(
        claims,
        audit_log=audit_log,
        date_from=_parse_date_param(from_, param_name="from"),
        date_to=_parse_date_param(to, end_of_day=True, param_name="to"),
        status=status,
        confidence=confidence,
        insurance=insurance,
        low_confidence_threshold=settings.low_confidence_threshold,
    )
    return {"success": True, "data": data}


@router.get("/dashboard/attention-summary")
def get_attention_summary():
    """Backs the header notification bell -- real claims that need attention,
    not a simulated notification count."""
    settings = get_settings()
    claims = claim_repository.list_all(include_deleted=False)
    return build_attention_summary(claims, low_confidence_threshold=settings.low_confidence_threshold)


@router.get("/dashboard/providers")
def list_insurance_providers():
    """Distinct provider names actually seen in claim data, for the filter dropdown."""
    claims = claim_repository.list_all(include_deleted=False)
    providers = {
        (c.get("fields", {}).get("insuranceCompany", {}).get("value") or "").strip() for c in claims
    }
    providers.discard("")
    return sorted(providers)


@router.get("/dashboard/export")
def export_dashboard(
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    status: str = Query("all"),
    confidence: str = Query("all"),
    insurance: str = Query("all"),
):
    claims = claim_repository.list_all(include_deleted=False)
    rows = build_export_rows(
        claims,
        date_from=_parse_date_param(from_, param_name="from"),
        date_to=_parse_date_param(to, end_of_day=True, param_name="to"),
        status=status,
        confidence=confidence,
        insurance=insurance,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Claim ID",
            "Filename",
            "Received At",
            "Status",
            "Match Score",
            "Confidence %",
            "Patient Name",
            "Insurance Company",
            "Claim Amount",
            "Approved Amount",
        ]
    )
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=claims_export.csv"},
    )
