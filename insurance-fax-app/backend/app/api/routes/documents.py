"""
Document upload + processing-status endpoints.

Routers stay thin: validate the request, call the orchestrator /
repository, return the result. No PDF parsing, AI prompting, or
business rules live here -- see app/agents/orchestrator.py and
app/services/* for that.
"""

import logging
import threading
import time
import uuid

from fastapi import APIRouter, File, UploadFile

from ...agents.orchestrator import run_pipeline
from ...core.config import get_settings
from ...core.exceptions import InvalidDocumentError, NotFoundError
from ...repositories.claim_repository import claim_repository
from ...repositories.upload_job_repository import upload_job_repository
from ...services.documents.relevance_service import DocumentRelevanceService
from ...services.extraction.claim_extraction_service import CANONICAL_FIELDS, ClaimExtractionService
from ...services.ai.factory import get_ai_provider

logger = logging.getLogger("app.documents")

router = APIRouter(tags=["documents"])


def _validate_pdf_upload(file: UploadFile, pdf_bytes: bytes) -> None:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise InvalidDocumentError("Please upload a valid PDF document.")

    content_type = (file.content_type or "").lower()
    if content_type and content_type != "application/pdf":
        raise InvalidDocumentError("Invalid document type. Only PDF files are supported.")

    if len(pdf_bytes) == 0:
        raise InvalidDocumentError("The uploaded document is empty.")

    settings = get_settings()
    if len(pdf_bytes) > settings.max_file_size_bytes:
        raise InvalidDocumentError("The uploaded PDF exceeds the maximum supported file size.")


def _finalize_uploaded_record(record: dict) -> None:
    """Shared by both the sync and async upload paths -- persists the record
    and writes the same audit trail either way."""
    claim_repository.add(record)
    claim_repository.append_audit(
        {
            "fax_id": record["id"],
            "claim_id": record["id"],
            "action": "document_uploaded",
            "timestamp": record["received_at"],
            "detail": f"Document analysis completed with match score {record.get('document', {}).get('matchScore', 0)}%",
        }
    )
    if record["status"] == "invalid":
        claim_repository.append_audit(
            {
                "fax_id": record["id"],
                "claim_id": record["id"],
                "action": "document_rejected",
                "timestamp": record["received_at"],
                "detail": record.get("document", {}).get("validationMessage"),
            }
        )


@router.post("/documents/upload")
@router.post("/faxes/upload")
async def upload_document(file: UploadFile = File(...)):
    """Accept a PDF and return the analyzed claim document result synchronously.

    Kept for existing callers/tests. The interactive UI uses the
    upload-async + upload-status pair below instead, so it can show real
    per-stage progress instead of one long blocking wait.
    """
    pdf_bytes = await file.read()
    _validate_pdf_upload(file, pdf_bytes)

    record = run_pipeline(pdf_bytes, file.filename)
    _finalize_uploaded_record(record)
    return record


# A plain OS thread rather than asyncio.create_task(): run_pipeline is a
# long, blocking, CPU-bound call, and a fire-and-forget asyncio task here
# turned out to be unreliable under the ASGI event loop actually driving
# this server (progress would sometimes freeze forever on whatever stage
# happened to be current when the loop stopped scheduling it) -- a plain
# daemon thread has no such dependency on event-loop task scheduling.
def _run_upload_job(job_id: str, pdf_bytes: bytes, filename: str) -> None:
    def on_progress(stage: str, label: str, percent: int) -> None:
        upload_job_repository.update(job_id, stage=stage, label=label, percent=percent)

    try:
        record = run_pipeline(pdf_bytes, filename, on_progress)
        _finalize_uploaded_record(record)
        upload_job_repository.complete(job_id, record)
    except Exception:
        logger.exception("upload_job_failed", extra={"job_id": job_id})
        upload_job_repository.fail(job_id, "Processing this document failed. Please try again.")


def _schedule_upload_job(job_id: str, pdf_bytes: bytes, filename: str) -> None:
    threading.Thread(target=_run_upload_job, args=(job_id, pdf_bytes, filename), daemon=True).start()


@router.post("/documents/upload-async")
@router.post("/faxes/upload-async")
async def upload_document_async(file: UploadFile = File(...)):
    """Starts processing in the background and returns a job id immediately;
    poll GET .../upload-status/{job_id} for real per-stage progress."""
    pdf_bytes = await file.read()
    _validate_pdf_upload(file, pdf_bytes)

    job_id = str(uuid.uuid4())[:8]
    upload_job_repository.create(job_id)
    _schedule_upload_job(job_id, pdf_bytes, file.filename)
    return {"jobId": job_id}


@router.get("/documents/upload-status/{job_id}")
@router.get("/faxes/upload-status/{job_id}")
def get_upload_job_status(job_id: str):
    job = upload_job_repository.get(job_id)
    if job is None:
        raise NotFoundError(f"Upload job '{job_id}' was not found.")
    return job


@router.get("/documents/{document_id}")
def get_document(document_id: str):
    return claim_repository.get(document_id)


@router.get("/documents/{document_id}/status")
def get_document_status(document_id: str):
    record = claim_repository.get(document_id)
    status_map = {"invalid": "INVALID", "needs_review": "REVIEW_REQUIRED", "auto_filled": "COMPLETED", "resolved": "COMPLETED"}
    return {
        "status": status_map.get(record["status"], record["status"].upper()),
        "matchScore": record.get("document", {}).get("matchScore", 0),
    }


@router.get("/documents/{document_id}/analysis")
def get_document_analysis(document_id: str):
    record = claim_repository.get(document_id)
    return {
        "document": record.get("document"),
        "fields": record.get("fields"),
        "overallConfidence": record.get("overall_confidence"),
        "needsReviewCount": record.get("needs_review_count"),
    }


@router.post("/documents/{document_id}/reprocess")
def reprocess_document(document_id: str):
    """Re-run classification + AI extraction against the already-extracted text.

    Does not require re-uploading the PDF -- the original page text captured
    at upload time is reused, so this reflects any AI provider config change
    without needing the raw bytes to be kept in memory.
    """
    record = claim_repository.get(document_id)
    pages = record.get("pages") or [record.get("raw_text", "")]
    full_text = record.get("raw_text", "")

    if not full_text or len(full_text.strip()) < 30:
        raise NotFoundError("This document has no extracted text to reprocess.")

    settings = get_settings()
    ai_provider = get_ai_provider(settings)
    extraction = ClaimExtractionService.extract(
        pages=pages, full_text=full_text, ai_provider=ai_provider, low_confidence_threshold=settings.low_confidence_threshold
    )
    extracted_count = sum(1 for f in extraction.fields.values() if f.value)
    relevance = DocumentRelevanceService.analyze(
        text=full_text,
        extracted_value_count=extracted_count,
        total_field_count=len(CANONICAL_FIELDS),
        invalid_threshold=settings.invalid_match_threshold,
        review_threshold=settings.review_match_threshold,
    )

    previous_fields = record.get("fields", {})
    normalized_fields = {}
    for name, f in extraction.fields.items():
        # Reprocessing must not silently overwrite a value the manager already
        # verified/corrected -- that would defeat the whole point of manager review.
        was_manager_verified = bool(previous_fields.get(name, {}).get("managerVerified"))
        if was_manager_verified:
            normalized_fields[name] = previous_fields[name]
            continue
        normalized_fields[name] = {
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

    record["fields"] = normalized_fields
    record["document"].update(
        {"matchScore": relevance.match_score, "status": relevance.status, "validationMessage": relevance.validation_message, "reasons": relevance.reasons}
    )
    record["extractionSource"] = extraction.extraction_source
    record["aiError"] = extraction.ai_error
    needs_review_count = sum(1 for f in extraction.fields.values() if f.value and f.legacy_status == "needs_review")
    record["needs_review_count"] = needs_review_count
    record["status"] = "invalid" if relevance.status == "invalid" else ("needs_review" if needs_review_count or relevance.status == "review_required" else "auto_filled")

    claim_repository.update(document_id, record)
    claim_repository.append_audit(
        {"fax_id": document_id, "claim_id": document_id, "action": "document_reprocessed", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    )
    return record
