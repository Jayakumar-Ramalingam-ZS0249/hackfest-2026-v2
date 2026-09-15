"""
PDF text extraction, with automatic OCR fallback and table-aware text.

Pipeline per page:
  1. Native text extraction (PyMuPDF) -- fast, no dependencies beyond PyMuPDF.
  2. Table text (pdfplumber) -- appended so line-item bills/forms aren't lost
     to PyMuPDF's plain-text flattening.
  3. If the combined native+table text for THAT page is still too short
     (e.g. a scanned/faxed page with no text layer), automatically render
     the page to an image and run Tesseract OCR on it. No manual "enable
     OCR" step -- this happens per-page, automatically.

Honesty matters here: the Tesseract *binary* is a native dependency this
process cannot install for itself (only the `pytesseract` Python wrapper is
pip-installable). If it isn't on PATH, OCR is reported as unavailable rather
than silently pretending it ran -- see `ocr_available` on the result.
"""

import io
import logging

try:
    import fitz  # PyMuPDF

    HAVE_FITZ = True
except ImportError:
    HAVE_FITZ = False

try:
    import pdfplumber

    HAVE_PDFPLUMBER = True
except ImportError:
    HAVE_PDFPLUMBER = False

try:
    import pytesseract
    from PIL import Image

    HAVE_PYTESSERACT = True
except ImportError:
    HAVE_PYTESSERACT = False

logger = logging.getLogger("app.services.pdf")

MIN_TEXT_LENGTH_FOR_NO_OCR = 30  # whole-document threshold (kept for backward compatibility)
PAGE_MIN_TEXT_LENGTH = 20  # per-page threshold that triggers OCR for that page
OCR_RENDER_DPI = 200


class PdfExtractionResult:
    def __init__(self, pages: list[str], needs_ocr: bool, is_corrupt: bool, ocr_used: bool = False, ocr_available: bool = True):
        self.pages = pages
        self.needs_ocr = needs_ocr
        self.is_corrupt = is_corrupt
        self.ocr_used = ocr_used
        self.ocr_available = ocr_available

    @property
    def full_text(self) -> str:
        return "\n".join(p for p in self.pages if p).strip()


def _extract_table_blocks(pdf_bytes: bytes, page_count: int) -> list[str]:
    """Returns one text block per page summarizing any detected tables, or "" if none/unavailable."""
    if not HAVE_PDFPLUMBER:
        return [""] * page_count

    try:
        blocks: list[str] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                if not tables:
                    blocks.append("")
                    continue
                lines = []
                for table in tables:
                    for row in table:
                        cells = [str(cell).strip() if cell is not None else "" for cell in row]
                        if any(cells):
                            lines.append(" | ".join(cells))
                blocks.append("TABLE:\n" + "\n".join(lines) if lines else "")
        while len(blocks) < page_count:
            blocks.append("")
        return blocks[:page_count]
    except Exception as exc:
        logger.warning("table_extraction_failed: %s", exc)
        return [""] * page_count


def _ocr_page(page) -> tuple[str, bool]:
    """Returns (ocr_text, tesseract_available). ocr_text is "" if OCR found nothing or failed."""
    if not HAVE_PYTESSERACT:
        return "", False

    try:
        pixmap = page.get_pixmap(dpi=OCR_RENDER_DPI)
        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        text = pytesseract.image_to_string(image)
        return (text or "").strip(), True
    except Exception as exc:
        # Covers pytesseract.TesseractNotFoundError and any other native-binary failure.
        logger.warning("ocr_unavailable: %s", exc)
        return "", False


class PdfExtractionService:
    @staticmethod
    def extract(pdf_bytes: bytes) -> PdfExtractionResult:
        if not pdf_bytes:
            return PdfExtractionResult(pages=[], needs_ocr=False, is_corrupt=True)

        if not HAVE_FITZ:
            return PdfExtractionResult(pages=[], needs_ocr=True, is_corrupt=False, ocr_available=False)

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            native_pages = [page.get_text("text") or "" for page in doc]
        except Exception:
            return PdfExtractionResult(pages=[], needs_ocr=False, is_corrupt=True)

        table_blocks = _extract_table_blocks(pdf_bytes, len(native_pages))

        final_pages: list[str] = []
        ocr_used = False
        ocr_available = True
        for index, page in enumerate(doc):
            text = native_pages[index]
            if table_blocks[index]:
                text = (text + "\n" + table_blocks[index]).strip()

            if len(text.strip()) < PAGE_MIN_TEXT_LENGTH:
                ocr_text, available = _ocr_page(page)
                if not available:
                    ocr_available = False
                if ocr_text:
                    text = (text + "\n" + ocr_text).strip()
                    ocr_used = True

            final_pages.append(text)

        combined_length = len("".join(final_pages).strip())
        needs_ocr = combined_length < MIN_TEXT_LENGTH_FOR_NO_OCR
        return PdfExtractionResult(
            pages=final_pages, needs_ocr=needs_ocr, is_corrupt=False, ocr_used=ocr_used, ocr_available=ocr_available
        )
