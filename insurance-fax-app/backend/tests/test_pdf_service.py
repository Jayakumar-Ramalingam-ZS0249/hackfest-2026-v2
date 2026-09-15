import unittest

import fitz

from app.services.documents.pdf_service import PdfExtractionService


def make_text_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text, fontsize=10)
    return doc.tobytes()


def make_blank_pdf() -> bytes:
    doc = fitz.open()
    doc.new_page()
    return doc.tobytes()


class PdfExtractionServiceTests(unittest.TestCase):
    def test_native_text_pdf_does_not_need_ocr(self):
        result = PdfExtractionService.extract(make_text_pdf("Patient Name: Raj Kumar\nDiagnosis: Flu\n" * 3))
        self.assertFalse(result.needs_ocr)
        self.assertIn("Raj Kumar", result.full_text)

    def test_blank_page_pdf_triggers_ocr_attempt_and_reports_availability_honestly(self):
        result = PdfExtractionService.extract(make_blank_pdf())
        self.assertTrue(result.needs_ocr)
        # Whether or not the Tesseract binary happens to be installed on this
        # machine, the result must accurately reflect what actually happened --
        # never silently claim OCR ran when nothing could be read.
        self.assertIsInstance(result.ocr_available, bool)
        self.assertEqual(result.full_text, "")

    def test_empty_bytes_is_reported_as_corrupt(self):
        result = PdfExtractionService.extract(b"")
        self.assertTrue(result.is_corrupt)

    def test_every_page_is_extracted_not_just_the_first(self):
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page()
            page.insert_text((50, 50), f"Page marker {i + 1}: Diagnosis {i + 1}", fontsize=10)
        result = PdfExtractionService.extract(doc.tobytes())
        self.assertEqual(len(result.pages), 3)
        for i in range(3):
            self.assertIn(f"Diagnosis {i + 1}", result.pages[i])


if __name__ == "__main__":
    unittest.main()
