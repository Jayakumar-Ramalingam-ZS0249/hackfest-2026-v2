"""
Preprocess agent + Extraction agent
=====================================

PREPROCESS AGENT (LLD section 3):
    Deskews, rotates, denoises and crops the fax image so OCR has a
    clean input. For this MVP we skip real image cleanup (that stays
    in the existing Rotation tool per the LLD) and go straight to text
    extraction from the uploaded PDF.

EXTRACTION AGENT (LLD section 3):
    Reads the page and produces structured JSON of every field it can
    find, with a confidence score per field.

    PRODUCTION NOTE: replace `extract_fields_from_text()` below with a
    real call to a vision-capable LLM (e.g. Claude) or a document AI
    service (AWS Textract / Azure Document Intelligence). This MVP uses
    a rule-based regex extractor instead, so the whole pipeline runs
    end-to-end with zero external API keys required. The confidence
    scores below are deterministic heuristics standing in for what a
    real OCR/LLM confidence score would look like.
"""

import re
import io

try:
    import fitz  # PyMuPDF
    HAVE_FITZ = True
except ImportError:
    HAVE_FITZ = False


# A realistic mock fax used as a fallback if PDF text extraction fails
# (e.g. a scanned image PDF with no embedded text layer and no OCR
# engine installed in this environment). This lets the demo still run
# end-to-end without requiring Tesseract to be installed.
FALLBACK_FAX_TEXT = """
METRO HEALTH FAX TRANSMISSION
DATE: 09/07/2026

Patient Name: Jonathan Reynolds
Member ID: MRN-8849-X
DOB: 11/14/1978
City: Springfield
State: IL

Rx: Lipitor 40mg tablets qty 30, sig: 1 tab daily at bedtime.
Physician Signature: Dr. Robert Vance, MD
"""


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Pull raw text out of an uploaded fax PDF.

    Tries embedded text first (works for most modern faxes that were
    generated digitally, e.g. e-fax services). Falls back to the mock
    fax text above if no text layer is found and no OCR engine is
    available — this keeps the demo runnable everywhere.
    """
    if not HAVE_FITZ:
        return FALLBACK_FAX_TEXT

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        combined = "\n".join(text_parts).strip()
        return combined if combined else FALLBACK_FAX_TEXT
    except Exception:
        # Any parsing failure -> fall back gracefully rather than crash
        # the whole pipeline. A production system would log this error
        # and route the fax straight to the "Needs Review" queue.
        return FALLBACK_FAX_TEXT


# ---------------------------------------------------------------
# CANONICAL FIELD SCHEMA (LLD section 4 - "Canonical field schema")
# ---------------------------------------------------------------
# Each entry: (canonical_field_name, [list of regex patterns to try])
# The first pattern that matches wins. In production this table is the
# "Mapping agent" — normalizing "DOB", "Date of Birth", "D.O.B." etc.
# onto one canonical name.
FIELD_PATTERNS = {
    "first_name": [r"Patient Name:\s*([A-Za-z.'-]+)\s+[A-Za-z.'-]+"],
    "last_name": [r"Patient Name:\s*[A-Za-z.'-]+\s+([A-Za-z.'-]+)"],
    "member_number": [r"(?:Member ID|Member Number|MRN)[:\s]*([A-Za-z0-9-]+)"],
    "dob": [r"DOB[:\s]*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})"],
    "city": [r"City[:\s]*([A-Za-z][A-Za-z\s]*[A-Za-z])(?=\s*\n)"],
    "state": [r"State[:\s]*([A-Za-z]{2,})"],
    "drug": [r"Rx[:\s]*([^,\n]+)"],
    "physician": [r"Physician Signature[:\s]*(Dr\.?\s*[A-Za-z.'\s]+)"],
}


def _confidence_for(field_name: str, matched: bool, raw_value: str) -> float:
    """
    Simplified confidence heuristic standing in for a real OCR/LLM
    confidence score. In production this number comes directly from
    the vision model or document-AI service response.

    We deliberately make member_number a bit noisier here (mirroring
    the reference screenshot's "82% Review" example) so the demo shows
    both the auto-fill and the flag-for-review paths.
    """
    if not matched or not raw_value.strip():
        return 0.0

    if field_name == "member_number":
        # Simulate the kind of OCR ambiguity that happens with mixed
        # letters/numbers/hyphens on a faxed document.
        return 0.82

    # Everything else: high confidence, small variation per field so
    # the UI doesn't show a suspiciously uniform 99% everywhere.
    base_scores = {
        "first_name": 0.99,
        "last_name": 0.99,
        "dob": 0.98,
        "city": 0.95,
        "state": 0.93,
        "drug": 0.90,
        "physician": 0.88,
    }
    return base_scores.get(field_name, 0.85)


def extract_fields_from_text(raw_text: str) -> dict:
    """
    THE EXTRACTION + MAPPING AGENTS, COMBINED FOR THIS MVP.

    Runs each canonical field's regex patterns against the raw fax
    text and returns a dict of:
        { field_name: {"value": str, "confidence": float} }

    Swap this function's internals for a real Claude/GPT-4V vision
    call or a Textract/Document-Intelligence API call in production —
    the OUTPUT SHAPE below is what the rest of the pipeline expects,
    so nothing downstream needs to change.
    """
    results = {}
    for field_name, patterns in FIELD_PATTERNS.items():
        matched_value = ""
        matched = False
        for pattern in patterns:
            m = re.search(pattern, raw_text, re.IGNORECASE)
            if m:
                matched_value = m.group(1).strip()
                matched = True
                break

        results[field_name] = {
            "value": matched_value,
            "confidence": round(_confidence_for(field_name, matched, matched_value), 2),
        }

    return results
