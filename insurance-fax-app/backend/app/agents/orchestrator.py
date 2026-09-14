"""
Pipeline orchestrator
=======================

Runs the stages in the exact order described in the LLD:

    1. Fax received
    2. Preprocess agent      (skipped here -- handled by existing tool)
    3. Extraction agent      -> extract_fields_from_text()
    4. Mapping agent         -> folded into extraction for this MVP
    5. Eligibility match agent -> run_eligibility_lookup()
    6. Confidence check      -> decide_field_status() per field
    7a/7b. Auto-fill vs Flag for review -> decided per field, no
           separate function call needed since it's just a label

This file is intentionally the ONLY place that calls the agent
functions in sequence -- exactly like the "Planner loop" in the
banking collections example: it orchestrates, but every real
computation happens inside the agent functions it calls.
"""

import time
import uuid

from .extraction import extract_text_from_pdf, extract_fields_from_text
from .eligibility import run_eligibility_lookup, decide_field_status


def _provenance(tool_name: str) -> dict:
    """Stamps a pipeline step with a timestamp and a run id -- the same
    'provenance tagger' idea from the collections architecture, kept
    lightweight here since this is a linear pipeline, not an LLM
    planner choosing tool order dynamically."""
    return {
        "tool": tool_name,
        "run_id": str(uuid.uuid4())[:8],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def run_pipeline(pdf_bytes: bytes, filename: str) -> dict:
    """
    Runs the full fax-intake pipeline on an uploaded PDF and returns a
    single record ready to store and display in the UI.
    """
    provenance_log = []

    # --- Step: Extraction agent -------------------------------------
    raw_text = extract_text_from_pdf(pdf_bytes)
    provenance_log.append(_provenance("extraction_agent"))

    extracted_fields = extract_fields_from_text(raw_text)
    provenance_log.append(_provenance("mapping_agent"))

    # --- Step: Eligibility match agent -------------------------------
    eligibility = run_eligibility_lookup(extracted_fields)
    provenance_log.append(_provenance("eligibility_match_agent"))

    # --- Step: Confidence / QA agent ---------------------------------
    field_results = {}
    confidences = []
    needs_review_count = 0

    for field_name, data in extracted_fields.items():
        status = decide_field_status(field_name, data["confidence"])
        if status == "needs_review":
            needs_review_count += 1
        field_results[field_name] = {
            "value": data["value"],
            "confidence": data["confidence"],
            "status": status,  # "auto_fill" or "needs_review"
        }
        confidences.append(data["confidence"])

    provenance_log.append(_provenance("confidence_qa_agent"))

    overall_confidence = round(
        (sum(confidences) / len(confidences)) * 100, 1
    ) if confidences else 0.0

    # If eligibility lookup failed to find the member, force the fax
    # into review no matter how confident the OCR was -- this mirrors
    # the LLD's rule that eligibility mismatches must always route to
    # a human.
    overall_status = "needs_review" if (needs_review_count > 0 or not eligibility["found"]) else "auto_filled"

    record = {
        "id": str(uuid.uuid4())[:8],
        "filename": filename,
        "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "raw_text": raw_text,
        "fields": field_results,
        "eligibility": eligibility,
        "overall_confidence": overall_confidence,
        "needs_review_count": needs_review_count,
        "status": overall_status,  # "auto_filled" | "needs_review" | "resolved"
        "provenance": provenance_log,
    }
    return record
