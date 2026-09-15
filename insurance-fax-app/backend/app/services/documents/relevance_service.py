"""
Document classification + relevance (match score) engine.

Deliberately stays deterministic/rule-based rather than an AI call:
classification and match scoring must be fast, free, and 100%
reproducible so the zero/low-match rejection path (see
DocumentRelevanceService.analyze) never depends on an external AI
provider being configured or available.
"""

from dataclasses import dataclass, field

DOCUMENT_TYPE_HINTS: dict[str, list[str]] = {
    "hospital_discharge_summary": ["hospital", "discharge", "admission", "diagnosis", "discharge date", "patient name"],
    "insurance_claim_form": ["claim number", "policy number", "insurance company", "member id", "claim amount"],
    "hospital_bill": ["hospital bill", "itemized bill", "consultation", "room charges", "total bill"],
    "medical_report": ["medical report", "treatment", "doctor", "diagnosis", "procedure"],
    "policy_document": ["policy number", "coverage", "sum insured", "member id", "plan"],
}

DOCUMENT_TYPE_LABELS = {
    "hospital_discharge_summary": "Hospital Discharge Summary",
    "insurance_claim_form": "Insurance Claim Form",
    "hospital_bill": "Hospital Bill",
    "medical_report": "Medical Report",
    "policy_document": "Insurance Policy",
}

# Configurable relevance-signal weights (section 9 of the spec: "use
# configurable weights, do not hardcode scoring logic throughout the code").
# Every signal below is worth SIGNAL_WEIGHT points, capped at MAX_SIGNAL_SCORE.
SIGNAL_WEIGHT = 5
MAX_SIGNAL_SCORE = 100

PATIENT_INDICATORS = ["patient", "patient name", "date of birth", "member id", "policy number"]
MEDICAL_INDICATORS = ["diagnosis", "admission", "discharge", "doctor", "hospital", "treatment"]
INSURANCE_INDICATORS = ["insurance company", "policy number", "member id", "claim number", "coverage", "preauthorization"]
CLAIM_INDICATORS = ["claim number", "claim amount", "approved amount", "hospital bill", "claim date"]

SIGNAL_GROUPS = {
    "Patient information detected": PATIENT_INDICATORS,
    "Medical/treatment information detected": MEDICAL_INDICATORS,
    "Insurance policy information detected": INSURANCE_INDICATORS,
    "Claim information detected": CLAIM_INDICATORS,
}


@dataclass
class RelevanceResult:
    document_type: str
    match_score: int
    status: str  # "invalid" | "review_required" | "valid"
    validation_message: str
    reasons: list[str] = field(default_factory=list)


class DocumentRelevanceService:
    @staticmethod
    def classify(text: str) -> str:
        lowercase = (text or "").lower()
        scores = {doc_type: sum(1 for hint in hints if hint in lowercase) for doc_type, hints in DOCUMENT_TYPE_HINTS.items()}
        best_type, best_score = max(scores.items(), key=lambda item: item[1], default=("Unknown", 0))
        if best_score == 0:
            return "Unknown"
        return DOCUMENT_TYPE_LABELS.get(best_type, "Other Medical Document")

    @staticmethod
    def _signal_reasons(text: str) -> tuple[int, list[str]]:
        lowercase = (text or "").lower()
        reasons = []
        signal_count = 0
        for reason, keywords in SIGNAL_GROUPS.items():
            hits = sum(1 for kw in keywords if kw in lowercase)
            if hits:
                signal_count += hits
                reasons.append(reason)
        return signal_count, reasons

    @staticmethod
    def analyze(
        text: str,
        extracted_value_count: int,
        total_field_count: int,
        invalid_threshold: int,
        review_threshold: int,
    ) -> RelevanceResult:
        if not text or len(text.strip()) < 30:
            return RelevanceResult(
                document_type="Unknown",
                match_score=0,
                status="invalid",
                validation_message="The uploaded document does not contain sufficient patient, medical, or claim-related information.",
                reasons=[],
            )

        document_type = DocumentRelevanceService.classify(text)
        signal_count, reasons = DocumentRelevanceService._signal_reasons(text)
        field_coverage_score = int((extracted_value_count / max(1, total_field_count)) * 100)
        match_score = min(MAX_SIGNAL_SCORE, max(0, signal_count * SIGNAL_WEIGHT + field_coverage_score) // 2 + min(signal_count * SIGNAL_WEIGHT, field_coverage_score) // 2)
        match_score = min(100, max(0, match_score))

        if match_score < invalid_threshold or document_type == "Unknown":
            return RelevanceResult(
                document_type=document_type,
                match_score=match_score,
                status="invalid",
                validation_message="This document does not contain sufficient insurance or claim-related information for this workflow.",
                reasons=reasons,
            )

        if match_score < review_threshold:
            return RelevanceResult(
                document_type=document_type,
                match_score=match_score,
                status="review_required",
                validation_message="This document may be related to the claim, but sufficient information could not be confidently identified.",
                reasons=reasons,
            )

        return RelevanceResult(
            document_type=document_type,
            match_score=match_score,
            status="valid",
            validation_message="Document validated for claim processing.",
            reasons=reasons,
        )
