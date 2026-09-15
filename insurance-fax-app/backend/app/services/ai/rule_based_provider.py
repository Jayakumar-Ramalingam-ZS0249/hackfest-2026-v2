"""
Deterministic, zero-dependency fallback AI provider.

Used when no AI_API_KEY is configured (or the real provider call
fails) so the application keeps running end-to-end without any
external service -- exactly the guarantee the original MVP made.
Extraction is regex-based; chat is unsupported (there is no model to
ground answers against), so ChatService must handle that gracefully
rather than pretending to answer.
"""

import re

from .base import AIFieldResult, AIProvider

# One canonical regex per field. Used both as the fallback extractor AND
# (in ClaimExtractionService) to cross-check every AI-extracted value
# against each page of the document for conflicting candidates.
FIELD_PATTERNS: dict[str, list[str]] = {
    # NOTE: value-capturing groups use a literal space (" "), never "\s", so a
    # match can never run past the end of its line into the next label --
    # "\s" also matches "\n", which previously let e.g. "Patient Name: Raj
    # Kumar\nDate of Birth: ..." get captured as "Raj Kumar\nDate of Birth".
    "patientName": [
        r"Patient\s*Name\s*[:\-]\s*([A-Z][A-Za-z. '-]+)",
        r"Name\s*[:\-]\s*([A-Z][A-Za-z. '-]+)",
        r"Insured\s*Name\s*[:\-]\s*([A-Z][A-Za-z. '-]+)",
    ],
    "dateOfBirth": [
        r"Date\s*of\s*Birth\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
        r"DOB\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
    ],
    "memberId": [
        r"Member\s*ID\s*[:\-]\s*([A-Za-z0-9-]+)",
        r"Member\s*No\.?\s*[:\-]\s*([A-Za-z0-9-]+)",
        r"Policy\s*Number\s*[:\-]\s*([A-Za-z0-9-]+)",
    ],
    "insuranceCompany": [
        r"Insurance\s*Company\s*[:\-]\s*([A-Za-z0-9&. '-]+)",
        r"Insurer\s*[:\-]\s*([A-Za-z0-9&. '-]+)",
    ],
    "policyNumber": [
        r"Policy\s*Number\s*[:\-]\s*([A-Za-z0-9-]+)",
        r"Policy\s*No\.?\s*[:\-]\s*([A-Za-z0-9-]+)",
    ],
    "claimNumber": [
        r"Claim\s*Number\s*[:\-]\s*([A-Za-z0-9-]+)",
        r"Claim\s*ID\s*[:\-]\s*([A-Za-z0-9-]+)",
    ],
    "hospitalName": [
        r"Hospital\s*Name\s*[:\-]\s*([A-Za-z0-9&. '-]+)",
        r"Hospital\s*[:\-]\s*([A-Za-z0-9&. '-]+)",
    ],
    "doctorName": [
        r"Doctor\s*Name\s*[:\-]\s*([A-Z][A-Za-z. '-]+)",
        r"Consulting\s*Doctor\s*[:\-]\s*([A-Z][A-Za-z. '-]+)",
    ],
    "diagnosis": [
        r"Diagnosis\s*[:\-]\s*([A-Za-z0-9/, .'-]+)",
        r"Primary\s*Diagnosis\s*[:\-]\s*([A-Za-z0-9/, .'-]+)",
    ],
    "admissionDate": [
        r"Admission\s*Date\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
        r"Admitted\s*On\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
    ],
    "dischargeDate": [
        r"Discharge\s*Date\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
        r"Discharged\s*On\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
    ],
    "claimAmount": [
        r"Total\s*Claim\s*Amount\s*[:\-]\s*([Rr]s\.?\s*[$\d,\.]+|\$\s*\d[\d,\.]+|\d[\d,\.]+)",
        r"Claim\s*Amount\s*[:\-]\s*([Rr]s\.?\s*[$\d,\.]+|\$\s*\d[\d,\.]+|\d[\d,\.]+)",
    ],
    "hospitalBillAmount": [
        r"Hospital\s*Bill\s*[:\-]\s*([Rr]s\.?\s*[$\d,\.]+|\$\s*\d[\d,\.]+|\d[\d,\.]+)",
    ],
    "approvedAmount": [
        r"Approved\s*Amount\s*[:\-]\s*([Rr]s\.?\s*[$\d,\.]+|\$\s*\d[\d,\.]+|\d[\d,\.]+)",
    ],
    "deductibleAmount": [
        r"Deductible\s*[:\-]\s*([Rr]s\.?\s*[$\d,\.]+|\$\s*\d[\d,\.]+|\d[\d,\.]+)",
    ],
}

BASE_CONFIDENCE = {
    "patientName": 0.96,
    "dateOfBirth": 0.95,
    "memberId": 0.88,
    "insuranceCompany": 0.9,
    "policyNumber": 0.9,
    "claimNumber": 0.92,
    "hospitalName": 0.93,
    "doctorName": 0.88,
    "diagnosis": 0.89,
    "admissionDate": 0.93,
    "dischargeDate": 0.93,
    "claimAmount": 0.86,
    "hospitalBillAmount": 0.84,
    "approvedAmount": 0.82,
    "deductibleAmount": 0.8,
}


def extract_field_from_text(field_name: str, text: str) -> AIFieldResult | None:
    """Run one field's regex patterns against a block of text (a page or the whole document)."""
    for pattern in FIELD_PATTERNS.get(field_name, []):
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            if value:
                return AIFieldResult(value=value, confidence=BASE_CONFIDENCE.get(field_name, 0.75), source_text=match.group(0).strip())
    return None


class RuleBasedProvider(AIProvider):
    name = "rule_based"
    supports_chat = False

    def extract_fields(self, document_text: str, field_names: list[str]) -> dict[str, AIFieldResult]:
        results: dict[str, AIFieldResult] = {}
        for field_name in field_names:
            found = extract_field_from_text(field_name, document_text or "")
            results[field_name] = found or AIFieldResult(value=None, confidence=0.0, source_text=None)
        return results
