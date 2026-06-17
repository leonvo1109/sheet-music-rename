from __future__ import annotations

import re

import fitz
from PIL import Image

from ocr_score_rename.instruments import Instrument, match_instrument
from ocr_score_rename.page_regions import _title_rect, extract_title_region_text_from_page
from ocr_score_rename.text_normalize import normalize_for_match

_MAX_TITLE_WORDS = 8
_MAX_TITLE_CHARS = 56
_MIN_TITLE_LENGTH = 6
_SIZE_TOLERANCE = 0.88

_PART_LABEL = re.compile(r"^\d+[\.\s]\s*\S", re.IGNORECASE)
_TITLE_PHRASE = re.compile(
    r"\b(in\s+harmonie\s+verein[t]?)(?:\s+(marsch))?",
    re.IGNORECASE,
)

_META_LINE = re.compile(
    r"\b(stimme|partitur|dirigent|seite|page|takt|tempo|metronom|copyright|verlag|edition|arr\.|bearb\.)\b",
    re.IGNORECASE,
)
_VOICE_NUMBER = re.compile(
    r"(?:"
    r"\b(?:[1-5]|i{1,3}|iv|solo)\s*\.?\s*(?:stimme|part|voice)?\s*$"
    r"|"
    r"^\d+[\.\s]\s*(?:stimme|part|voice)\b"
    r"|"
    r"\b(?:[1-5]|i{1,3}|iv)\s*$"
    r")",
    re.IGNORECASE,
)
_IN_TONALITY = re.compile(
    r"\bin\s+(?:b|es|ess|e[sß]|f|c|a|eb|bb|bp|bo|bd|sib)(?:[\s-]|dur|flat|major|$)",
    re.IGNORECASE,
)
_MUSIC_DIRECTION = re.compile(
    r"\b(allegro|andante|vivace|maestoso|dolce|adagio|moderato|rit\.?|accel\.?|marc\.?)\b",
    re.IGNORECASE,
)
_DYNAMICS = re.compile(r"\b(?:fff|ff|mf|mp|pp|sfz|sf|fz|fp|f|p)\b", re.IGNORECASE)
_GARBAGE_LINE = re.compile(r"^[\W\d_=<>\-—–·•]{0,3}[\W\d_=<>\-—–·•]$|^[a-zA-Z]$")


def _clean_title(text: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", text.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" .,-;:")


def _instrument_terms(instruments: list[Instrument] | None) -> set[str]:
    terms: set[str] = set()
    for instrument in instruments or []:
        for value in (instrument.name, *instrument.synonyms):
            normalized = normalize_for_match(value)
            if len(normalized) >= 4:
                terms.add(normalized)
    return terms


def _is_noise_line(text: str, instrument_terms: set[str]) -> bool:
    cleaned = _clean_title(text)
    if len(cleaned) < 2:
        return True
    if _GARBAGE_LINE.match(cleaned):
        return True

    normalized = normalize_for_match(cleaned)
    if _META_LINE.search(normalized):
        return True
    if _VOICE_NUMBER.search(normalized):
        return True
    if _IN_TONALITY.search(normalized):
        return True
    if _MUSIC_DIRECTION.search(normalized):
        return True
    if _DYNAMICS.fullmatch(normalized) or (
        len(normalized) <= 4 and _DYNAMICS.search(normalized)
    ):
        return True
    if len(cleaned) > _MAX_TITLE_CHARS:
        return True
    if len(cleaned.split()) > _MAX_TITLE_WORDS:
        return True
    if sum(char.isdigit() for char in cleaned) > len(cleaned) * 0.35:
        return True

    letters = sum(char.isalpha() for char in cleaned)
    if letters < len(cleaned) * 0.4:
        return True

    for term in instrument_terms:
        if term in normalized:
            return True

    return False


def is_acceptable_title(text: str, *, instruments: list[Instrument] | None = None) -> bool:
    cleaned = _clean_title(text)
    if len(cleaned) < _MIN_TITLE_LENGTH:
        return False
    instrument_terms = _instrument_terms(instruments)
    if _is_noise_line(cleaned, instrument_terms):
        return False
    words = cleaned.split()
    if len(words) == 1 and len(cleaned) < 10:
        return False
    return True


def _is_instrument_line(line: str, instruments: list[Instrument] | None) -> bool:
    if match_instrument(line, instruments or []):
        return True
    if not _PART_LABEL.match(line):
        return False
    normalized = normalize_for_match(line)
    return any(term in normalized for term in _instrument_terms(instruments))


def extract_work_title_from_header(
    header_text: str,
    instruments: list[Instrument] | None = None,
) -> str | None:
    """Werktitel steht bei Blasorchester-Scans meist im Kopfbereich über oder neben der Stimmenzeile."""
    flattened = re.sub(r"\s+", " ", header_text)
    phrase = _TITLE_PHRASE.search(flattened)
    if phrase:
        title = _clean_title(" ".join(group for group in phrase.groups() if group))
        if is_acceptable_title(title, instruments=instruments):
            return title

    instrument_terms = _instrument_terms(instruments)
    lines = [_clean_title(line) for line in header_text.splitlines()]
    lines = [line for line in lines if line]

    title_parts: list[str] = []
    for line in lines:
        if _is_instrument_line(line, instruments):
            break
        if _is_noise_line(line, instrument_terms):
            continue
        title_parts.append(line)

    if not title_parts:
        for line in lines:
            if _is_instrument_line(line, instruments):
                continue
            if _is_noise_line(line, instrument_terms):
                continue
            title_parts.append(line)
            if len(title_parts) >= 3:
                break

    title = _clean_title(" ".join(title_parts))
    return title if is_acceptable_title(title, instruments=instruments) else None


def _pick_best_line(candidates: list[tuple[float, float, float, str]], instrument_terms: set[str]) -> str | None:
    if not candidates:
        return None

    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    max_size = candidates[0][0]
    if max_size <= 0:
        return None

    for size, _y, _x, text in candidates:
        if size < max_size * _SIZE_TOLERANCE:
            break
        cleaned = _clean_title(text)
        if not _is_noise_line(cleaned, instrument_terms):
            return cleaned
    return None


def _lines_from_embedded(page: fitz.Page, region: fitz.Rect) -> list[tuple[float, float, float, str]]:
    candidates: list[tuple[float, float, float, str]] = []
    for block in page.get_text("dict", clip=region)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            parts: list[str] = []
            line_size = 0.0
            line_y = 0.0
            line_x = 0.0
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                size = float(span.get("size", 0))
                x0, y0, _, _ = span["bbox"]
                parts.append(text)
                line_size = max(line_size, size)
                line_y = y0 if not line_y else min(line_y, y0)
                line_x = x0 if not line_x else min(line_x, x0)
            if parts:
                candidates.append((line_size, line_y, line_x, _clean_title(" ".join(parts))))
    return candidates


def _lines_from_ocr_text(text: str, instrument_terms: set[str]) -> str | None:
    candidates: list[tuple[float, float, float, str]] = []
    for index, raw_line in enumerate(text.splitlines()):
        cleaned = _clean_title(raw_line)
        if not cleaned:
            continue
        score = max(1.0, 100.0 - index * 12.0)
        candidates.append((score, float(index), 0.0, cleaned))
    return _pick_best_line(candidates, instrument_terms)


def extract_title_from_page(
    page: fitz.Page,
    image: Image.Image,
    *,
    instruments: list[Instrument] | None = None,
    header_text: str | None = None,
) -> str | None:
    if header_text is not None:
        title = extract_work_title_from_header(header_text, instruments)
        if title:
            return title

    instrument_terms = _instrument_terms(instruments)
    region = _title_rect(page)

    embedded_lines = _lines_from_embedded(page, region)
    title = _pick_best_line(embedded_lines, instrument_terms)
    if title and is_acceptable_title(title, instruments=instruments):
        return title

    ocr_text = extract_title_region_text_from_page(page, image)
    ocr_title = _lines_from_ocr_text(ocr_text, instrument_terms)
    if ocr_title and is_acceptable_title(ocr_title, instruments=instruments):
        return ocr_title
    return None


def detect_batch_title(
    header_texts: list[str],
    instruments: list[Instrument] | None = None,
) -> str | None:
    from collections import Counter

    titles = [
        title
        for header in header_texts
        if (title := extract_work_title_from_header(header, instruments))
    ]
    if not titles:
        return None
    with_marsch = [title for title in titles if "marsch" in normalize_for_match(title)]
    if with_marsch:
        return Counter(with_marsch).most_common(1)[0][0]
    return Counter(titles).most_common(1)[0][0]
