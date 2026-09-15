"""
Claim listing, retrieval, and human-review decision endpoints.

/api/faxes/* are the original endpoint names the existing Angular app
already calls -- kept working unchanged. /api/claims/* are additive
aliases using the claim-centric naming the rest of the new workflow
uses; both paths share the exact same repository/service calls so
there is no duplicated logic.
"""

import time

from fastapi import APIRouter

from ...repositories.claim_repository import claim_repository
from ...schemas.claim import DecisionPayload

router = APIRouter(tags=["claims"])


def _summary(record: dict) -> dict:
    return {
        "id": record["id"],
        "filename": record["filename"],
        "received_at": record["received_at"],
        "status": record["status"],
        "overall_confidence": record["overall_confidence"],
        "needs_review_count": record["needs_review_count"],
        "matchScore": record.get("document", {}).get("matchScore", 0),
    }


@router.get("/faxes")
@router.get("/claims")
def list_claims():
    return [_summary(r) for r in claim_repository.list_all()]


@router.get("/faxes/{claim_id}")
@router.get("/claims/{claim_id}")
def get_claim(claim_id: str):
    return claim_repository.get(claim_id)


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
