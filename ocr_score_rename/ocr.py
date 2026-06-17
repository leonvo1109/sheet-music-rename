from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytesseract
from PIL import Image

from ocr_score_rename.tesseract_runtime import configure_tesseract

_MIN_EMBEDDED_LETTERS = 10
_RENDER_MATRIX = fitz.Matrix(2, 2)


def embedded_text_sufficient(text: str, *, min_letters: int = _MIN_EMBEDDED_LETTERS) -> bool:
    return sum(1 for char in text if char.isalpha()) >= min_letters


def render_page_image(page: fitz.Page) -> Image.Image:
    pixmap = page.get_pixmap(matrix=_RENDER_MATRIX, alpha=False)
    return Image.open(io.BytesIO(pixmap.tobytes("png")))


def extract_text_from_page(page: fitz.Page) -> str:
    """Use embedded PDF text when present; otherwise OCR the rendered page."""
    embedded = page.get_text("text").strip()
    if embedded_text_sufficient(embedded):
        return embedded

    configure_tesseract()
    return pytesseract.image_to_string(render_page_image(page))


def load_page_image(pdf_path: Path, page_index: int = 0) -> Image.Image:
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            return Image.new("RGB", (1, 1), "white")
        page = doc.load_page(min(page_index, doc.page_count - 1))
        return render_page_image(page)


def extract_page_content(pdf_path: Path, page_index: int = 0) -> tuple[str, Image.Image]:
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            empty = Image.new("RGB", (1, 1), "white")
            return "", empty
        page = doc.load_page(min(page_index, doc.page_count - 1))
        return extract_text_from_page(page), render_page_image(page)


def extract_text_from_pdf(pdf_path: Path, page_index: int = 0) -> str:
    """Extract text from a PDF page (embedded text or OCR for pure scans)."""
    text, _image = extract_page_content(pdf_path, page_index)
    return text
