import unittest

from app.services.documents.relevance_service import DocumentRelevanceService
from app.services.extraction.claim_extraction_service import CANONICAL_FIELDS


class DocumentRelevanceServiceTests(unittest.TestCase):
    def test_valid_claim_document_is_relevant(self):
        text = """
        Hospital Name: City General Hospital
        Patient Name: Raj Kumar
        Date of Birth: 12/03/1985
        Policy Number: ABC123456
        Claim Number: CLM-2026-4567
        Admission Date: 12/08/2026
        Discharge Date: 15/08/2026
        Diagnosis: Acute pancreatitis
        Total Claim Amount: Rs. 85000
        Insurance Company: Star Health
        Member ID: M-24567
        """
        result = DocumentRelevanceService.analyze(
            text=text,
            extracted_value_count=11,
            total_field_count=len(CANONICAL_FIELDS),
            invalid_threshold=25,
            review_threshold=60,
        )
        self.assertGreater(result.match_score, 60)
        self.assertEqual(result.document_type, "Hospital Discharge Summary")
        self.assertEqual(result.status, "valid")

    def test_irrelevant_document_is_rejected(self):
        text = """
        Welcome to our newsletter. Summer sale starts today.
        Buy our products and save 40%.
        """
        result = DocumentRelevanceService.analyze(
            text=text,
            extracted_value_count=0,
            total_field_count=len(CANONICAL_FIELDS),
            invalid_threshold=25,
            review_threshold=60,
        )
        self.assertLessEqual(result.match_score, 25)
        self.assertEqual(result.status, "invalid")

    def test_empty_document_is_invalid_with_zero_score(self):
        result = DocumentRelevanceService.analyze(
            text="",
            extracted_value_count=0,
            total_field_count=len(CANONICAL_FIELDS),
            invalid_threshold=25,
            review_threshold=60,
        )
        self.assertEqual(result.match_score, 0)
        self.assertEqual(result.status, "invalid")


if __name__ == "__main__":
    unittest.main()
