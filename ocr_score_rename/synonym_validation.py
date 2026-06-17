from __future__ import annotations

import re

from ocr_score_rename.instruments import Instrument
from ocr_score_rename.text_normalize import normalize_for_match, normalized_key

_MIN_SYNONYM_LENGTH = 2
_INVALID_SYNONYM = re.compile(r"[<>:\"/\\|?*]")


def validate_synonym(
    synonym: str,
    *,
    instrument: Instrument,
    all_instruments: list[Instrument],
) -> str | None:
    """Return a German error message, or None if the synonym is valid."""
    cleaned = synonym.strip()
    if not cleaned:
        return "Synonym darf nicht leer sein."
    if _INVALID_SYNONYM.search(cleaned):
        return "Synonym enthält ungültige Dateizeichen."

    normalized = normalize_for_match(cleaned)
    if len(normalized) < _MIN_SYNONYM_LENGTH:
        return "Synonym ist nach Normalisierung zu kurz."

    key = normalized_key(cleaned)
    for existing in instrument.synonyms:
        if normalized_key(existing) == key:
            return "Dieses Synonym existiert bereits (Groß-/Kleinschreibung und Apostrophe werden ignoriert)."

    for other in all_instruments:
        if other.name == instrument.name:
            continue
        if normalized_key(other.name) == key:
            return f"Kollidiert mit Instrument „{other.name}“."
        for other_synonym in other.synonyms:
            if normalized_key(other_synonym) == key:
                return f"Kollidiert mit Synonym „{other_synonym}“ von „{other.name}“."

    return None
