from __future__ import annotations

import io

import fitz
import pytesseract
from PIL import Image

from ocr_score_rename.ocr import embedded_text_sufficient
from ocr_score_rename.tesseract_runtime import configure_tesseract

# Kopfbereich: nur die obere linke Ecke (Stimmenbezeichnung, kein Notentext).
HEADER_TOP_FRACTION = 0.22
HEADER_LEFT_FRACTION = 0.72

# Titel: etwas größer, aber weiterhin nur links oben.
TITLE_TOP_FRACTION = 0.24
TITLE_LEFT_FRACTION = 0.58


def crop_region(image: Image.Image, *, top_fraction: float, left_fraction: float) -> Image.Image:
    width, height = image.size
    return image.crop((0, 0, int(width * left_fraction), int(height * top_fraction)))


def _header_rect(page: fitz.Page) -> fitz.Rect:
    rect = page.rect
    return fitz.Rect(0, 0, rect.width * HEADER_LEFT_FRACTION, rect.height * HEADER_TOP_FRACTION)


def _title_rect(page: fitz.Page) -> fitz.Rect:
    rect = page.rect
    return fitz.Rect(0, 0, rect.width * TITLE_LEFT_FRACTION, rect.height * TITLE_TOP_FRACTION)


def extract_region_text_from_page(page: fitz.Page, region: fitz.Rect) -> str:
    clipped = page.get_text("text", clip=region).strip()
    if embedded_text_sufficient(clipped):
        return clipped

    configure_tesseract()
    matrix = fitz.Matrix(2, 2)
    pixmap = page.get_pixmap(matrix=matrix, clip=region, alpha=False)
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    return pytesseract.image_to_string(image)


def extract_header_text_from_page(page: fitz.Page, image: Image.Image | None = None) -> str:
    text = extract_region_text_from_page(page, _header_rect(page))
    if embedded_text_sufficient(text):
        return text
    if image is not None:
        crop = crop_region(image, top_fraction=HEADER_TOP_FRACTION, left_fraction=HEADER_LEFT_FRACTION)
        configure_tesseract()
        return pytesseract.image_to_string(crop)
    return text


def extract_title_region_text_from_page(page: fitz.Page, image: Image.Image | None = None) -> str:
    text = extract_region_text_from_page(page, _title_rect(page))
    if embedded_text_sufficient(text):
        return text
    if image is not None:
        crop = crop_region(image, top_fraction=TITLE_TOP_FRACTION, left_fraction=TITLE_LEFT_FRACTION)
        configure_tesseract()
        return pytesseract.image_to_string(crop)
    return text
