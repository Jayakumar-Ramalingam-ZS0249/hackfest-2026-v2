"""
Dashboard analytics.

Every number this module returns is computed from the real in-memory
claim/audit store passed in by the caller -- there is no synthetic or
random data anywhere here. Sections with no real signal (e.g. no claim
has a parseable amount yet) report an explicit "not available" state
rather than fabricating a value.
"""

import re
from collections import defaultdict
from datetime import datetime

from ..chat.chat_service import FIELD_LABELS

CONFIDENCE_HIGH_CUTOFF = 0.85

ACTION_LABELS = {
    "document_uploaded": "Document Uploaded",
    "document_rejected": "Document Rejected",
    "document_deleted": "Claim Deleted",
    "document_restored": "Claim Restored",
    "document_reprocessed": "Document Reprocessed",
    "field_corrected": "Field Corrected",
    "decision_submitted": "Decision Submitted",
    "chat_question_asked": "AI Question Asked",
}

STATUS_LABELS = {
    "auto_filled": "Queued",
    "needs_review": "Needs Review",
    "resolved": "Resolved",
    "invalid": "Invalid",
}


def _parse_amount(value) -> float | None:
    if not value:
        return None
    match = re.search(r"[\d,]+(?:\.\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def _field_value(record: dict, name: str):
    return record.get("fields", {}).get(name, {}).get("value")


def confidence_bucket(overall_confidence_pct: float) -> str:
    """overall_confidence on a claim record is stored 0-100."""
    if overall_confidence_pct >= 85:
        return "high"
    if overall_confidence_pct >= 70:
        return "medium"
    return "low"


def apply_filters(claims: list[dict], *, date_from, date_to, status, confidence, insurance) -> list[dict]:
    result = []
    for c in claims:
        received = _parse_timestamp(c.get("received_at"))
        if date_from and received and received < date_from:
            continue
        if date_to and received and received > date_to:
            continue
        if status and status != "all" and c.get("status") != status:
            continue
        if confidence and confidence != "all":
            if confidence == "needs_review":
                if c.get("status") != "needs_review":
                    continue
            elif confidence_bucket(c.get("overall_confidence") or 0) != confidence:
                continue
        if insurance and insurance != "all":
            provider = (_field_value(c, "insuranceCompany") or "").strip().lower()
            if provider != insurance.strip().lower():
                continue
        result.append(c)
    return result


def _claim_issues(claim: dict, low_confidence_threshold: float) -> list[tuple[str, str]]:
    """Returns (reason, priority) pairs for a single claim, most severe first."""
    issues: list[tuple[str, str]] = []
    if claim.get("status") == "invalid":
        issues.append(("Invalid document -- failed relevance check", "HIGH"))
    for name, f in claim.get("fields", {}).items():
        label = FIELD_LABELS.get(name, name)
        if f.get("conflicts"):
            issues.append((f"Conflicting values found for {label}", "HIGH"))
    for name, f in claim.get("fields", {}).items():
        label = FIELD_LABELS.get(name, name)
        if f.get("value") and (f.get("confidence") is not None) and f["confidence"] < low_confidence_threshold:
            issues.append((f"Low confidence on {label}", "MEDIUM"))
    if claim.get("status") == "needs_review" and not issues:
        issues.append(("Manual review required", "MEDIUM"))
    return issues


def build_overview(
    claims: list[dict],
    *,
    audit_log: list[dict],
    date_from,
    date_to,
    status: str,
    confidence: str,
    insurance: str,
    low_confidence_threshold: float,
) -> dict:
    filtered = apply_filters(
        claims, date_from=date_from, date_to=date_to, status=status, confidence=confidence, insurance=insurance
    )
    filtered_ids = {c["id"] for c in filtered}
    total = len(filtered)

    by_status: dict[str, int] = defaultdict(int)
    for c in filtered:
        by_status[c.get("status", "unknown")] += 1

    summary = {
        "totalClaims": total,
        "pendingReview": by_status.get("needs_review", 0),
        "queued": by_status.get("auto_filled", 0),
        "resolved": by_status.get("resolved", 0),
        "invalid": by_status.get("invalid", 0),
    }

    # --- Financial summary -------------------------------------------------
    total_claim_value = 0.0
    approved_value = 0.0
    pending_value = 0.0
    rejected_value = 0.0
    any_amount_found = False
    for c in filtered:
        amount = _parse_amount(_field_value(c, "claimAmount"))
        if amount is None:
            continue
        any_amount_found = True
        total_claim_value += amount
        if c["status"] == "resolved":
            approved_value += _parse_amount(_field_value(c, "approvedAmount")) or amount
        elif c["status"] in ("needs_review", "auto_filled"):
            pending_value += amount
        elif c["status"] == "invalid":
            rejected_value += amount

    financial = (
        {
            "available": True,
            "currency": "INR",
            "totalClaimValue": round(total_claim_value, 2),
            "approvedValue": round(approved_value, 2),
            "pendingValue": round(pending_value, 2),
            "rejectedValue": round(rejected_value, 2),
        }
        if any_amount_found
        else {"available": False}
    )

    # --- Status distribution (real percentages, not hardcoded) -------------
    status_distribution = []
    for key, label in STATUS_LABELS.items():
        count = by_status.get(key, 0)
        pct = round((count / total) * 100, 1) if total else 0
        status_distribution.append({"status": label, "count": count, "percentage": pct})

    # --- Document / OCR analytics -------------------------------------------
    ocr_required = sum(1 for c in filtered if c.get("document", {}).get("needsOcr"))
    ocr_completed = sum(1 for c in filtered if c.get("document", {}).get("ocrUsed"))
    document_analytics = {
        "uploaded": total,
        "processed": by_status.get("resolved", 0) + by_status.get("needs_review", 0) + by_status.get("auto_filled", 0),
        "ocrRequired": ocr_required,
        "ocrCompleted": ocr_completed,
        "invalid": by_status.get("invalid", 0),
    }

    # --- Field-level AI/OCR quality -----------------------------------------
    high = medium = low = 0
    verified_sources = 0
    total_fields_with_value = 0
    for c in filtered:
        for f in c.get("fields", {}).values():
            if not f.get("value"):
                continue
            total_fields_with_value += 1
            conf = f.get("confidence") or 0.0
            if conf >= CONFIDENCE_HIGH_CUTOFF:
                high += 1
            elif conf >= low_confidence_threshold:
                medium += 1
            else:
                low += 1
            if f.get("sourceText"):
                verified_sources += 1

    quality = {
        "highConfidenceFields": high,
        "mediumConfidenceFields": medium,
        "lowConfidenceFields": low,
        "documentsRequiringReview": by_status.get("needs_review", 0),
        "ocrDocuments": ocr_completed,
        "validationFailures": by_status.get("invalid", 0),
        "sourceMappingSuccessRate": round((verified_sources / total_fields_with_value) * 100, 1)
        if total_fields_with_value
        else 0,
    }

    # --- Insurance provider analytics ---------------------------------------
    provider_map: dict[str, dict] = {}
    for c in filtered:
        provider = (_field_value(c, "insuranceCompany") or "").strip()
        if not provider:
            continue
        entry = provider_map.setdefault(
            provider, {"provider": provider, "claims": 0, "totalValue": 0.0, "approved": 0, "pending": 0}
        )
        entry["claims"] += 1
        entry["totalValue"] += _parse_amount(_field_value(c, "claimAmount")) or 0.0
        if c["status"] == "resolved":
            entry["approved"] += 1
        elif c["status"] in ("needs_review", "auto_filled"):
            entry["pending"] += 1
    insurance_providers = sorted(provider_map.values(), key=lambda p: p["claims"], reverse=True)
    for p in insurance_providers:
        p["totalValue"] = round(p["totalValue"], 2)

    # --- Trend (daily buckets across whatever range is filtered) ------------
    trend_map: dict[str, dict] = {}
    status_to_trend_key = {"resolved": "resolved", "needs_review": "needsReview", "invalid": "invalid", "auto_filled": "queued"}
    for c in filtered:
        received = _parse_timestamp(c.get("received_at"))
        if not received:
            continue
        day = received.strftime("%Y-%m-%d")
        bucket = trend_map.setdefault(
            day, {"date": day, "submitted": 0, "resolved": 0, "needsReview": 0, "invalid": 0, "queued": 0}
        )
        bucket["submitted"] += 1
        bucket[status_to_trend_key.get(c["status"], "queued")] += 1
    trends = sorted(trend_map.values(), key=lambda b: b["date"])

    # --- Recent activity: global audit log, scoped to the filtered claims ---
    recent_activity = []
    for entry in audit_log:
        claim_id = entry.get("claim_id") or entry.get("fax_id")
        if claim_id not in filtered_ids:
            continue
        claim = next((c for c in filtered if c["id"] == claim_id), None)
        recent_activity.append(
            {
                "timestamp": entry.get("timestamp"),
                "claimId": claim_id,
                "patient": _field_value(claim, "patientName") if claim else None,
                "action": ACTION_LABELS.get(entry.get("action"), entry.get("action") or "Unknown"),
                "status": claim.get("status") if claim else None,
                "user": entry.get("reviewer") or "system",
            }
        )
    recent_activity.sort(key=lambda a: a["timestamp"] or "", reverse=True)
    recent_activity = recent_activity[:20]

    # --- Attention required --------------------------------------------------
    attention_required = []
    for c in filtered:
        issues = _claim_issues(c, low_confidence_threshold)
        if not issues:
            continue
        reason, priority = issues[0]
        attention_required.append(
            {
                "claimId": c["id"],
                "filename": c.get("filename"),
                "reason": reason,
                "priority": priority,
                "issueCount": len(issues),
                "lastUpdated": c.get("received_at"),
                "matchScore": c.get("document", {}).get("matchScore", 0),
            }
        )
    priority_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    attention_required.sort(key=lambda a: (priority_rank.get(a["priority"], 3), a["lastUpdated"] or ""), reverse=False)
    attention_required = attention_required[:20]

    return {
        "summary": summary,
        "financial": financial,
        "statusDistribution": status_distribution,
        "documentAnalytics": document_analytics,
        "quality": quality,
        "insuranceProviders": insurance_providers,
        "trends": trends,
        "recentActivity": recent_activity,
        "attentionRequired": attention_required,
    }


def build_attention_summary(claims: list[dict], *, low_confidence_threshold: float, limit: int = 8) -> dict:
    """Lightweight version of the attentionRequired section, for the header
    notification bell -- real counts/claims, not a fabricated badge number."""
    items = []
    for c in claims:
        if c.get("deleted"):
            continue
        issues = _claim_issues(c, low_confidence_threshold)
        if not issues:
            continue
        reason, priority = issues[0]
        items.append(
            {
                "claimId": c["id"],
                "filename": c.get("filename"),
                "reason": reason,
                "priority": priority,
                "lastUpdated": c.get("received_at"),
            }
        )
    priority_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    items.sort(key=lambda a: (priority_rank.get(a["priority"], 3), a["lastUpdated"] or ""), reverse=False)
    return {"count": len(items), "items": items[:limit]}


def build_export_rows(claims: list[dict], *, date_from, date_to, status, confidence, insurance) -> list[list[str]]:
    filtered = apply_filters(
        claims, date_from=date_from, date_to=date_to, status=status, confidence=confidence, insurance=insurance
    )
    rows = []
    for c in filtered:
        rows.append(
            [
                c["id"],
                c.get("filename", ""),
                c.get("received_at", ""),
                c.get("status", ""),
                c.get("document", {}).get("matchScore", 0),
                c.get("overall_confidence", 0),
                _field_value(c, "patientName") or "",
                _field_value(c, "insuranceCompany") or "",
                _field_value(c, "claimAmount") or "",
                _field_value(c, "approvedAmount") or "",
            ]
        )
    return rows
