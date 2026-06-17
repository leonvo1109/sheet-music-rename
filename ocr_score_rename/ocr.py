from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytesseract
from PIL import Image

from ocr_score_rename.tesseract_runtime import configure_tesseract

# Enough letters to trust an embedded text layer (digital scores, scanner OCR).
_MIN_EMBEDDED_LETTERS = 10


def embedded_text_sufficient(text: str, *, min_letters: int = _MIN_EMBEDDED_LETTERS) -> bool:
    return sum(1 for char in text if char.isalpha()) >= min_letters


def extract_text_from_page(page: fitz.Page) -> str:
    """Use embedded PDF text when present; otherwise OCR the rendered page."""
    embedded = page.get_text("text").strip()
    if embedded_text_sufficient(embedded):
        return embedded

    configure_tesseract()
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    return pytesseract.image_to_string(image)


def extract_text_from_pdf(pdf_path: Path, page_index: int = 0) -> str:
    """Extract text from a PDF page (embedded text or OCR for pure scans)."""
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            return ""
        page = doc.load_page(min(page_index, doc.page_count - 1))
        return extract_text_from_page(page)
