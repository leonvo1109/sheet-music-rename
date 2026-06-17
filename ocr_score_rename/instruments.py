from __future__ import annotations

import re
from dataclasses import dataclass

from ocr_score_rename.text_normalize import normalize_for_match, normalized_key

# Short codes used in filenames when Stimmung differs from the default.
TUNING_CODES: dict[str, str] = {
    "E": "E",  # Es / E-flat
    "B": "B",  # B-flat (German notation)
    "F": "F",
    "C": "C",
    "A": "A",
}

TUNING_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "E",
        re.compile(
            r"(?:in[\s-]+(?:es|ess|e[sß])|e[\s-]?flat|eb[\s-]?flat|mi[\s-]?bemol(?:le)?)\b",
            re.IGNORECASE,
        ),
    ),
        (
            "B",
            re.compile(
                r"(?:"
                r"in[\s-]+b(?:[\s-]?(?:flat|dur|p|o|d))?"
                r"|b[\s-]dur"
                r"|bb[\s-]?flat"
                r"|si[\s-]?bemol(?:le)?"
                r"|sib\b"
                r"|in[\s-]+sib"
                r")\b",
                re.IGNORECASE,
            ),
        ),
    ("F", re.compile(r"(?:in[\s-]+f(?:[\s-]?(?:dur|major))?|f[\s-]dur)\b", re.IGNORECASE)),
    ("C", re.compile(r"(?:in[\s-]+c(?:[\s-]?(?:dur|major))?|c[\s-]dur)\b", re.IGNORECASE)),
    ("A", re.compile(r"(?:in[\s-]+a(?:[\s-]?(?:dur|major))?|a[\s-]dur)\b", re.IGNORECASE)),
]


@dataclass(frozen=True)
class Instrument:
    name: str
    tuning: str
    synonyms: tuple[str, ...]


@dataclass(frozen=True)
class MatchResult:
    name: str
    standard_tuning: str
    detected_tuning: str


def parse_instruments(parsed: dict) -> list[Instrument]:
    instruments: list[Instrument] = []
    for entry in parsed.get("instruments", []):
        name = str(entry["name"]).strip()
        if not name:
            continue
        tuning = str(entry.get("tuning") or "").strip().upper()
        raw_synonyms = entry.get("synonyms") or []
        synonyms: list[str] = [name]
        seen = {normalized_key(name)}
        for synonym in raw_synonyms:
            cleaned = str(synonym).strip()
            if not cleaned:
                continue
            key = normalized_key(cleaned)
            if key in seen:
                continue
            seen.add(key)
            synonyms.append(cleaned)
        instruments.append(Instrument(name=name, tuning=tuning, synonyms=tuple(synonyms)))
    return instruments


def _synonym_pattern(normalized_synonym: str) -> re.Pattern[str]:
    escaped = re.escape(normalized_synonym)
    if normalized_synonym.endswith("."):
        return re.compile(rf"(?<![a-z0-9]){escaped}")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


def _find_synonym_position(normalized_text: str, normalized_synonym: str) -> int | None:
    if not normalized_synonym:
        return None
    match = _synonym_pattern(normalized_synonym).search(normalized_text)
    return match.start() if match else None


def detect_tuning(text: str, *, position: int, matched_synonym: str, fallback: str) -> str:
    for source in (
        normalize_for_match(matched_synonym),
        normalize_for_match(text[max(0, position - 30) : position + 120]),
    ):
        for code, pattern in TUNING_PATTERNS:
            if pattern.search(source):
                return code
    return fallback.upper() if fallback else ""


def tuning_for_filename(standard: str, detected: str, *, include_when_known: bool) -> str | None:
    standard_code = (standard or "").upper()
    detected_code = (detected or "").upper()

    if detected_code and standard_code and detected_code != standard_code:
        return TUNING_CODES.get(detected_code, detected_code)
    if include_when_known and standard_code:
        return TUNING_CODES.get(standard_code, standard_code)
    if include_when_known and detected_code:
        return TUNING_CODES.get(detected_code, detected_code)
    return None


def tuning_suffix(standard: str, detected: str) -> str | None:
    """Backward-compatible: only non-standard tunings."""
    return tuning_for_filename(standard, detected, include_when_known=False)


def _synonym_allowed(normalized_synonym: str) -> bool:
    if len(normalized_synonym) >= 4:
        return True
    return len(normalized_synonym) >= 2 and normalized_synonym.endswith(".")


def pick_instrument_label_text(text: str, instruments: list[Instrument]) -> str:
    """Use the best single header line for instrument matching."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return text.strip()

    scored: list[tuple[int, int, str]] = []
    for line in lines:
        if len(line) > 50:
            continue
        if not match_instrument(line, instruments):
            continue
        score = 100 - len(line)
        if re.match(r"^\d+[\.\s]", line):
            score += 200
        if line.startswith("("):
            score -= 80
        scored.append((score, len(line), line))

    if scored:
        scored.sort(key=lambda item: (-item[0], item[1]))
        return scored[0][2]

    for line in lines:
        if len(line) <= 50 and re.match(r"^\d+[\.\s]", line):
            return line

    return ""


def match_instrument(ocr_text: str, instruments: list[Instrument]) -> MatchResult | None:
    """Return instrument name and detected tuning for the best synonym match."""
    if not ocr_text.strip():
        return None

    normalized = normalize_for_match(ocr_text)
    candidates: list[tuple[int, int, Instrument, str]] = []

    for instrument in instruments:
        for synonym in instrument.synonyms:
            norm_synonym = normalize_for_match(synonym)
            if not _synonym_allowed(norm_synonym):
                continue
            position = _find_synonym_position(normalized, norm_synonym)
            if position is None:
                continue
            candidates.append((position, len(norm_synonym), instrument, synonym))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], -item[1]))
    instrument, matched_synonym = candidates[0][2], candidates[0][3]
    position = candidates[0][0]
    detected = detect_tuning(
        ocr_text,
        position=position,
        matched_synonym=matched_synonym,
        fallback=instrument.tuning,
    )
    return MatchResult(
        name=instrument.name,
        standard_tuning=instrument.tuning,
        detected_tuning=detected,
    )
