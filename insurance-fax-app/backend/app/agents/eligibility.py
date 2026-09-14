"""
Eligibility match agent + Confidence / QA agent
==================================================

ELIGIBILITY MATCH AGENT (LLD section 3):
    Takes the extracted Member Number, Name and DOB and queries the
    patient/eligibility database to auto-populate read-only fields
    (Client, Plan, Group No., Eligibility Status, etc.).

CONFIDENCE / QA AGENT (LLD section 3):
    Decides per field whether to auto-fill (high confidence + DB
    match) or flag for review (low confidence or no match). This is
    deliberately simple threshold logic -- NO LLM involved -- because
    this step touches the live patient database and must stay
    deterministic and auditable.
"""

from ..mock_db import lookup_member


# Tunable per-field confidence thresholds (LLD section 4 -
# "Confidence threshold config"). Member Number is held to a much
# higher bar because it drives the eligibility lookup below -- a wrong
# member number could pull up the WRONG patient's record.
CONFIDENCE_THRESHOLDS = {
    "member_number": 0.95,
    "first_name": 0.90,
    "last_name": 0.90,
    "dob": 0.90,
    "city": 0.70,
    "state": 0.70,
    "drug": 0.85,
    "physician": 0.80,
}

DEFAULT_THRESHOLD = 0.85


def decide_field_status(field_name: str, confidence: float) -> str:
    """
    Returns "auto_fill" or "needs_review" for a single field based on
    its confidence score and the configured threshold for that field.
    """
    threshold = CONFIDENCE_THRESHOLDS.get(field_name, DEFAULT_THRESHOLD)
    return "auto_fill" if confidence >= threshold else "needs_review"


def run_eligibility_lookup(extracted_fields: dict) -> dict:
    """
    Looks up the extracted member number in the eligibility database
    and returns the read-only fields to display alongside the
    editable patient fields.

    If the member number isn't found (or wasn't extracted with enough
    confidence to trust), the whole fax is forced into a review state
    regardless of how confident the OCR was on other fields -- an
    eligibility mismatch is exactly the kind of error a human MUST
    catch before this fax is resolved.
    """
    member_field = extracted_fields.get("member_number", {})
    member_number = member_field.get("value", "")
    member_confidence = member_field.get("confidence", 0.0)

    eligibility_record = None
    if member_number and member_confidence >= CONFIDENCE_THRESHOLDS["member_number"]:
        eligibility_record = lookup_member(member_number)
    else:
        # Even a high-confidence OCR read is meaningless if the member
        # number doesn't actually exist in the eligibility system --
        # still try the lookup so the UI can show "No match found".
        eligibility_record = lookup_member(member_number) if member_number else None

    if eligibility_record:
        return {
            "found": True,
            **eligibility_record,
        }

    return {
        "found": False,
        "client": None,
        "plan": None,
        "group_no": None,
        "eligibility_status": "Not Found",
    }
