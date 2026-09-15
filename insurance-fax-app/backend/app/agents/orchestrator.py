"""
Pipeline orchestrator.

The single place that runs the document-processing pipeline stages in
order and assembles the claim record the rest of the app persists and
serves. Every stage is delegated to its own service -- this file only
sequences them.

    1. PDF text extraction        -> PdfExtractionService
    2. Document classification +
       relevance/match score      -> DocumentRelevanceService
    3. Zero/low match short-circuit (no fabricated fields for
       irrelevant documents -- see RULE 8)
    4. AI claim field extraction,
       source verification,
       conflict detection         -> ClaimExtractionService
    5. Eligibility lookup         -> run_eligibility_lookup()
"""

import time
import uuid

from ..core.config import get_settings
from ..services.ai.factory import get_ai_provider
from ..services.documents.pdf_service import PdfExtractionService
from ..services.documents.relevance_service import DocumentRelevanceService
from ..services.extraction.claim_extraction_service import CANONICAL_FIELDS, ClaimExtractionService
from .eligibility import run_eligibility_lookup


def _provenance(tool_name: str) -> dict:
    return {
        "tool": tool_name,
        "run_id": str(uuid.uuid4())[:8],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _empty_eligibility() -> dict:
    return {"found": False, "client": None, "plan": None, "group_no": None, "eligibility_status": "Not Found"}


def run_pipeline(pdf_bytes: bytes, filename: str) -> dict:
    settings = get_settings()
    provenance_log = [_provenance("pdf_extraction")]

    pdf_result = PdfExtractionService.extract(pdf_bytes)
    raw_text = pdf_result.full_text

    relevance = DocumentRelevanceService.analyze(
        text=raw_text,
        extracted_value_count=0,
        total_field_count=len(CANONICAL_FIELDS),
        invalid_threshold=settings.invalid_match_threshold,
        review_threshold=settings.review_match_threshold,
    )
    provenance_log.append(_provenance("relevance_analysis"))

    document_info = {
        "documentType": relevance.document_type,
        "matchScore": relevance.match_score,
        "status": relevance.status,
        "validationMessage": relevance.validation_message,
        "reasons": relevance.reasons,
        "needsOcr": pdf_result.needs_ocr,
        "ocrUsed": pdf_result.ocr_used,
        "ocrAvailable": pdf_result.ocr_available,
    }

    if relevance.status == "invalid":
        # RULE 8: an irrelevant/invalid document NEVER gets a fabricated
        # extraction record. Return the record with empty fields so the
        # frontend shows the validation modal instead of populated data.
        record = {
            "id": str(uuid.uuid4())[:8],
            "filename": filename,
            "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "raw_text": raw_text,
            "fields": {},
            "eligibility": _empty_eligibility(),
            "document": {**document_info, "summary": "No data available"},
            "overall_confidence": 0,
            "needs_review_count": 0,
            "status": "invalid",
            "provenance": provenance_log,
            "extractionSource": None,
            "aiError": None,
        }
        return record

    ai_provider = get_ai_provider(settings)
    extraction = ClaimExtractionService.extract(
        pages=pdf_result.pages,
        full_text=raw_text,
        ai_provider=ai_provider,
        low_confidence_threshold=settings.low_confidence_threshold,
    )
    provenance_log.append(_provenance(f"claim_extraction:{extraction.extraction_source}"))

    # Recompute relevance now that we know how many fields were actually
    # extracted, so the match score reflects real field coverage.
    extracted_count = sum(1 for f in extraction.fields.values() if f.value)
    relevance = DocumentRelevanceService.analyze(
        text=raw_text,
        extracted_value_count=extracted_count,
        total_field_count=len(CANONICAL_FIELDS),
        invalid_threshold=settings.invalid_match_threshold,
        review_threshold=settings.review_match_threshold,
    )
    document_info.update(
        {
            "matchScore": relevance.match_score,
            "status": relevance.status,
            "validationMessage": relevance.validation_message,
            "reasons": relevance.reasons,
        }
    )

    normalized_fields: dict[str, dict] = {}
    for field_name, f in extraction.fields.items():
        normalized_fields[field_name] = {
            "value": f.value,
            "confidence": f.confidence,
            "status": f.legacy_status,
            "sourceText": f.source_text,
            "validationStatus": f.status,
            "page": f.page,
            "verificationStatus": f.verification_status,
            "conflicts": [{"page": c.page, "value": c.value} for c in f.conflicts],
            "managerVerified": False,
        }

    member_field = normalized_fields.get("memberId", {})
    eligibility = run_eligibility_lookup(
        {"member_number": {"value": member_field.get("value") or "", "confidence": member_field.get("confidence") or 0.0}}
    )

    confidences = [f.confidence for f in extraction.fields.values() if f.value]
    overall_confidence = round((sum(confidences) / len(confidences)) * 100, 1) if confidences else 0
    needs_review_count = sum(1 for f in extraction.fields.values() if f.value and f.legacy_status == "needs_review")

    summary_parts = []
    for name in ("patientName", "hospitalName", "diagnosis", "claimAmount"):
        f = extraction.fields.get(name)
        if f and f.value:
            label = {"patientName": "Patient", "hospitalName": "Hospital", "diagnosis": "Diagnosis", "claimAmount": "Claim Amount"}[name]
            summary_parts.append(f"{label}: {f.value}")
    document_info["summary"] = " | ".join(summary_parts) if summary_parts else "No data available"

    status = "needs_review" if needs_review_count or relevance.status == "review_required" else "auto_filled"

    record = {
        "id": str(uuid.uuid4())[:8],
        "filename": filename,
        "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "raw_text": raw_text,
        "pages": pdf_result.pages,
        "fields": normalized_fields,
        "eligibility": eligibility,
        "document": document_info,
        "overall_confidence": overall_confidence,
        "needs_review_count": needs_review_count,
        "status": status,
        "provenance": provenance_log,
        "extractionSource": extraction.extraction_source,
        "aiError": extraction.ai_error,
    }
    return record
