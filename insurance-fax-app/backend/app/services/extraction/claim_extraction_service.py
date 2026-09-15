"""
Claim field extraction, orchestrated.

This is where RULE 1/2/6/7/9 from the spec are actually enforced in
code (not just prompted for):

  - The AI provider is asked to extract fields; if it's unavailable or
    errors out, we fall back to the deterministic regex extractor so
    the app never just shows nothing.
  - Every AI-returned value is source-verified: its sourceText (or the
    value itself) must literally appear in the document text, or the
    field is marked UNVERIFIED rather than trusted blindly.
  - Every field is independently checked for conflicts by re-running
    the regex pattern for that field against EACH page and collecting
    distinct values -- if more than one distinct value is found across
    pages, the field is flagged CONFLICT with every candidate kept.
  - A field with no value anywhere becomes value=null / NOT_FOUND /
    confidence=0. Nothing is ever guessed.
"""

from dataclasses import dataclass, field as dataclass_field

from ..ai.base import AIProvider
from ..ai.rule_based_provider import extract_field_from_text

CANONICAL_FIELDS: list[str] = [
    "patientName",
    "dateOfBirth",
    "memberId",
    "insuranceCompany",
    "policyNumber",
    "claimNumber",
    "hospitalName",
    "doctorName",
    "diagnosis",
    "admissionDate",
    "dischargeDate",
    "claimAmount",
    "hospitalBillAmount",
    "approvedAmount",
    "deductibleAmount",
]

FIELD_SECTIONS: dict[str, str] = {
    "patientName": "patient",
    "dateOfBirth": "patient",
    "memberId": "insurance",
    "insuranceCompany": "insurance",
    "policyNumber": "insurance",
    "claimNumber": "insurance",
    "hospitalName": "hospital",
    "doctorName": "hospital",
    "admissionDate": "hospital",
    "dischargeDate": "hospital",
    "diagnosis": "medical",
    "claimAmount": "financial",
    "hospitalBillAmount": "financial",
    "approvedAmount": "financial",
    "deductibleAmount": "financial",
}


@dataclass
class ConflictCandidate:
    page: int
    value: str


@dataclass
class ExtractedField:
    field_name: str
    value: str | None
    confidence: float
    status: str  # "verified" | "review_required" | "unverified" | "conflict" | "not_found"
    legacy_status: str  # "auto_fill" | "needs_review" | "not_found" -- keeps the existing Angular UI working unchanged
    page: int | None
    source_text: str | None
    verification_status: str  # "VERIFIED" | "UNVERIFIED" | "NOT_APPLICABLE"
    conflicts: list[ConflictCandidate] = dataclass_field(default_factory=list)
    manager_verified: bool = False  # true once a human manager has confirmed/corrected this value


@dataclass
class ExtractionResult:
    fields: dict[str, ExtractedField]
    extraction_source: str  # "ai" | "rule_based"
    ai_error: str | None


def _find_page_for_text(pages: list[str], needle: str | None) -> int | None:
    if not needle:
        return None
    needle_lower = needle.strip().lower()
    if not needle_lower:
        return None
    for index, page_text in enumerate(pages):
        if needle_lower in (page_text or "").lower():
            return index + 1
    return None


def _detect_conflicts(field_name: str, pages: list[str]) -> list[ConflictCandidate]:
    seen: dict[str, int] = {}
    for index, page_text in enumerate(pages):
        found = extract_field_from_text(field_name, page_text or "")
        if found and found.value:
            normalized = found.value.strip().lower()
            if normalized not in seen:
                seen[normalized] = index + 1

    if len(seen) <= 1:
        return []
    return [ConflictCandidate(page=page, value=value_lower) for value_lower, page in seen.items()]


class ClaimExtractionService:
    @staticmethod
    def extract(
        pages: list[str],
        full_text: str,
        ai_provider: AIProvider,
        low_confidence_threshold: float,
    ) -> ExtractionResult:
        ai_error: str | None = None
        ai_results = None
        extraction_source = ai_provider.name
        if ai_provider.name != "rule_based":
            try:
                ai_results = ai_provider.extract_fields(full_text, CANONICAL_FIELDS)
            except Exception as exc:  # AIProviderError or anything unexpected from the SDK
                ai_error = str(exc)
                extraction_source = "rule_based"

        if not ai_results:
            from ..ai.rule_based_provider import RuleBasedProvider

            ai_results = RuleBasedProvider().extract_fields(full_text, CANONICAL_FIELDS)
            extraction_source = "rule_based"

        fields: dict[str, ExtractedField] = {}
        for field_name in CANONICAL_FIELDS:
            result = ai_results.get(field_name)
            value = result.value if result else None
            confidence = result.confidence if result else 0.0
            source_text = result.source_text if result else None

            conflicts = _detect_conflicts(field_name, pages) if pages else []

            if not value:
                fields[field_name] = ExtractedField(
                    field_name=field_name,
                    value=None,
                    confidence=0.0,
                    status="not_found",
                    legacy_status="not_found",
                    page=None,
                    source_text=None,
                    verification_status="NOT_APPLICABLE",
                    conflicts=conflicts,
                )
                continue

            page_number = _find_page_for_text(pages, source_text) or _find_page_for_text(pages, value)
            verified = (source_text and source_text.lower() in full_text.lower()) or (value.lower() in full_text.lower())
            verification_status = "VERIFIED" if verified else "UNVERIFIED"

            if conflicts:
                status = "conflict"
            elif not verified:
                status = "unverified"
            elif confidence < low_confidence_threshold:
                status = "review_required"
            else:
                status = "verified"

            legacy_status = "auto_fill" if status == "verified" else "needs_review"

            fields[field_name] = ExtractedField(
                field_name=field_name,
                value=value,
                confidence=round(confidence, 2),
                status=status,
                legacy_status=legacy_status,
                page=page_number,
                source_text=source_text,
                verification_status=verification_status,
                conflicts=conflicts,
            )

        return ExtractionResult(fields=fields, extraction_source=extraction_source, ai_error=ai_error)
