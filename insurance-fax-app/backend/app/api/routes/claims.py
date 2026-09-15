"""
Claim listing, retrieval, and human-review decision endpoints.

/api/faxes/* are the original endpoint names the existing Angular app
already calls -- kept working unchanged. /api/claims/* are additive
aliases using the claim-centric naming the rest of the new workflow
uses; both paths share the exact same repository/service calls so
there is no duplicated logic.
"""

import time

from fastapi import APIRouter, Query

from ...core.exceptions import AppError
from ...repositories.claim_repository import claim_repository
from ...schemas.claim import DecisionPayload

router = APIRouter(tags=["claims"])

# Maps a sidebar/nav filter name to the predicate used to select claims for
# it. Only filters with a real, honest backing in the data model are
# supported here -- "Sent" and "Locked" from the original static sidebar
# mockup have no corresponding concept anywhere in this app (no downstream
# send integration, no record locking), so they are intentionally not
# wired up to fake data; see the frontend nav for how they're handled.
STATUS_FILTERS = {
    "all": lambda r: not r.get("deleted"),
    "needs_review": lambda r: not r.get("deleted") and r["status"] == "needs_review",
    "resolved": lambda r: not r.get("deleted") and r["status"] == "resolved",
    "invalid": lambda r: not r.get("deleted") and r["status"] == "invalid",
    "queued": lambda r: not r.get("deleted") and r["status"] == "auto_filled",
    "deleted": lambda r: bool(r.get("deleted")),
}


def _summary(record: dict) -> dict:
    return {
        "id": record["id"],
        "filename": record["filename"],
        "received_at": record["received_at"],
        "status": record["status"],
        "overall_confidence": record["overall_confidence"],
        "needs_review_count": record["needs_review_count"],
        "matchScore": record.get("document", {}).get("matchScore", 0),
        "deleted": bool(record.get("deleted")),
        "patientName": record.get("fields", {}).get("patientName", {}).get("value"),
    }


@router.get("/faxes")
@router.get("/claims")
def list_claims(status: str = Query("all", description="all | needs_review | resolved | invalid | queued | deleted")):
    predicate = STATUS_FILTERS.get(status)
    if predicate is None:
        raise AppError(f"Unknown status filter '{status}'.", code="INVALID_FILTER", status_code=400)
    return [_summary(r) for r in claim_repository.list_all(include_deleted=True) if predicate(r)]


@router.get("/faxes/{claim_id}")
@router.get("/claims/{claim_id}")
def get_claim(claim_id: str):
    return claim_repository.get(claim_id)


@router.delete("/faxes/{claim_id}")
@router.delete("/claims/{claim_id}")
def delete_claim(claim_id: str):
    record = claim_repository.get(claim_id)
    record["deleted"] = True
    record["deleted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    claim_repository.update(claim_id, record)
    claim_repository.append_audit(
        {"fax_id": claim_id, "claim_id": claim_id, "action": "document_deleted", "timestamp": record["deleted_at"]}
    )
    return {"success": True}


@router.post("/faxes/{claim_id}/restore")
@router.post("/claims/{claim_id}/restore")
def restore_claim(claim_id: str):
    record = claim_repository.get(claim_id)
    record["deleted"] = False
    record.pop("deleted_at", None)
    claim_repository.update(claim_id, record)
    claim_repository.append_audit(
        {
            "fax_id": claim_id,
            "claim_id": claim_id,
            "action": "document_restored",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    return record


def _apply_decision(claim_id: str, payload: DecisionPayload) -> dict:
    record = claim_repository.get(claim_id)

    if payload.corrections:
        for field_name, corrected_value in payload.corrections.items():
            if field_name in record["fields"]:
                original_value = record["fields"][field_name]["value"]
                if original_value == corrected_value:
                    continue
                record["fields"][field_name]["value"] = corrected_value
                record["fields"][field_name]["status"] = "auto_fill"
                record["fields"][field_name]["validationStatus"] = "verified"
                record["fields"][field_name]["managerVerified"] = True
                claim_repository.append_audit(
                    {
                        "fax_id": claim_id,
                        "claim_id": claim_id,
                        "action": "field_corrected",
                        "field": field_name,
                        "original_value": original_value,
                        "corrected_value": corrected_value,
                        "reviewer": payload.reviewer,
                        "reason": payload.reason,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                )

    record["status"] = "resolved" if payload.approved else "needs_review"
    record["needs_review_count"] = sum(1 for f in record["fields"].values() if f["status"] == "needs_review")

    claim_repository.append_audit(
        {
            "fax_id": claim_id,
            "claim_id": claim_id,
            "action": "decision_submitted",
            "approved": payload.approved,
            "reviewer": payload.reviewer,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )

    claim_repository.update(claim_id, record)
    return record


@router.post("/faxes/{claim_id}/decision")
def submit_decision(claim_id: str, payload: DecisionPayload):
    return _apply_decision(claim_id, payload)


@router.put("/claims/{claim_id}")
def update_claim(claim_id: str, payload: DecisionPayload):
    return _apply_decision(claim_id, payload)


@router.get("/faxes/{claim_id}/audit-log")
@router.get("/claims/{claim_id}/audit-log")
def get_audit_log(claim_id: str):
    claim_repository.get(claim_id)  # 404s if it doesn't exist
    return claim_repository.get_audit_log(claim_id)
