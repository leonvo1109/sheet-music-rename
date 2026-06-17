from __future__ import annotations

import re
import unicodedata

APOSTROPHE_CHARS = "''`´ʼ'‘’‚‛\""
UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "ae", "Ö": "oe", "Ü": "ue", "ß": "ss"})


def normalize_for_match(text: str) -> str:
    """Lowercase, fold umlauts, strip apostrophes/punctuation for robust matching."""
    normalized = unicodedata.normalize("NFKC", text).translate(UMLAUT_MAP).lower()
    for char in APOSTROPHE_CHARS:
        normalized = normalized.replace(char, "")
    normalized = re.sub(r"[^\w\s-]", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def normalized_key(text: str) -> str:
    return normalize_for_match(text).replace(" ", "")
