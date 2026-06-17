from __future__ import annotations

import re

from PIL import Image

from ocr_score_rename.clef_vision import detect_clef_from_image
from ocr_score_rename.text_normalize import normalize_for_match

CLEF_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("VSl", re.compile(r"\b(violinschluessel|violinschlüssel|treble clef|g clef|g-schluessel)\b", re.IGNORECASE)),
    ("BSl", re.compile(r"\b(bassschluessel|bassschlüssel|bass clef|f clef|f-schluessel)\b", re.IGNORECASE)),
    ("CAl", re.compile(r"\b(altschlüssel|altschluessel|alto clef|c clef)\b", re.IGNORECASE)),
]

TEXT_CONFIDENCE = 0.8
IMAGE_OVERRIDE_MARGIN = 0.12


def detect_clef_from_text(text: str) -> tuple[str | None, float]:
    normalized = normalize_for_match(text)
    for code, pattern in CLEF_PATTERNS:
        if pattern.search(normalized):
            return code, TEXT_CONFIDENCE
    return None, 0.0


def detect_clef(text: str, *, image: Image.Image | None = None) -> str | None:
    """Detect clef from scan image and OCR text, preferring the stronger signal."""
    text_result, text_confidence = detect_clef_from_text(text)
    if image is None:
        return text_result

    image_result, image_confidence = detect_clef_from_image(image)
    if image_result is None:
        return text_result
    if text_result is None:
        return image_result
    if image_result == text_result:
        return image_result
    if image_confidence >= text_confidence + IMAGE_OVERRIDE_MARGIN:
        return image_result
    return text_result
