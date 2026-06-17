from __future__ import annotations

import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ocr_score_rename.config import load_instruments
from ocr_score_rename.instruments import Instrument, match_instrument, tuning_suffix
from ocr_score_rename.ocr import extract_text_from_pdf


@dataclass
class RenameResult:
    source: Path
    destination: Path
    instrument: str | None
    prefix: str


def _sanitize_filename_part(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", value.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def build_output_name(
    *,
    instrument: str | None,
    number: int,
    score_title: str,
    extension: str,
    tuning: str | None = None,
) -> str:
    title = _sanitize_filename_part(score_title)
    if instrument:
        if tuning:
            return f"{instrument}_{tuning}_{number}_{title}{extension}"
        return f"{instrument}{number}_{title}{extension}"
    return f"unknown_{number}_{title}{extension}"


def process_pdfs(
    pdf_paths: list[Path],
    output_dir: Path,
    score_title: str,
    instruments: list[Instrument] | None = None,
) -> list[RenameResult]:
    """Copy PDFs to output_dir with instrument-based prefixes."""
    if not pdf_paths:
        return []

    instruments = instruments or load_instruments()
    output_dir.mkdir(parents=True, exist_ok=True)

    instrument_counts: dict[tuple[str, str | None], int] = defaultdict(int)
    unknown_count = 0
    results: list[RenameResult] = []

    for pdf_path in pdf_paths:
        ocr_text = extract_text_from_pdf(pdf_path)
        match = match_instrument(ocr_text, instruments)

        if match:
            suffix = tuning_suffix(match.standard_tuning, match.detected_tuning)
            count_key = (match.name, suffix)
            instrument_counts[count_key] += 1
            number = instrument_counts[count_key]
            if suffix:
                prefix = f"{match.name}_{suffix}_{number}"
            else:
                prefix = f"{match.name}{number}"
            instrument_label = match.name
        else:
            unknown_count += 1
            number = unknown_count
            prefix = f"unknown_{number}_"
            suffix = None
            instrument_label = None

        output_name = build_output_name(
            instrument=instrument_label,
            tuning=suffix,
            number=number,
            score_title=score_title,
            extension=pdf_path.suffix or ".pdf",
        )
        destination = output_dir / output_name
        shutil.copy2(pdf_path, destination)
        results.append(
            RenameResult(
                source=pdf_path,
                destination=destination,
                instrument=instrument_label,
                prefix=prefix,
            )
        )

    return results
