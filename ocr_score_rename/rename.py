from __future__ import annotations

import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import fitz

from ocr_score_rename.clef import detect_clef
from ocr_score_rename.config import load_instruments
from ocr_score_rename.instruments import Instrument, match_instrument, pick_instrument_label_text, tuning_for_filename
from ocr_score_rename.naming import NamingSettings, VoiceParts, build_output_name
from ocr_score_rename.ocr import render_page_image
from ocr_score_rename.page_regions import extract_header_text_from_page
from ocr_score_rename.title import detect_batch_title, extract_work_title_from_header, is_acceptable_title


@dataclass
class RenameResult:
    source: Path
    destination: Path
    instrument: str | None
    prefix: str
    title: str


def list_pdfs_in_directory(directory: Path) -> list[Path]:
    return sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _count_key(
    *,
    instrument: str,
    tuning: str | None,
    clef: str | None,
) -> tuple[str, str | None, str | None]:
    return (instrument, tuning, clef)


def process_pdfs(
    pdf_paths: list[Path],
    output_dir: Path,
    score_title: str | None,
    instruments: list[Instrument] | None = None,
    *,
    naming: NamingSettings | None = None,
    in_place: bool = False,
    auto_detect_title: bool = False,
) -> list[RenameResult]:
    """Rename or copy PDFs with instrument-based filenames."""
    if not pdf_paths:
        return []

    instruments = instruments or load_instruments()
    naming = naming or NamingSettings()
    output_dir.mkdir(parents=True, exist_ok=True)

    instrument_counts: dict[tuple[str, str | None, str | None], int] = defaultdict(int)
    unknown_count = 0
    results: list[RenameResult] = []

    batch_title = (score_title or "").strip() or None
    if auto_detect_title:
        header_samples: list[str] = []
        sample_paths = sorted(pdf_paths, key=lambda path: path.name.lower())[:8]
        for pdf_path in sample_paths:
            with fitz.open(pdf_path) as doc:
                if doc.page_count == 0:
                    continue
                page = doc.load_page(0)
                header_samples.append(extract_header_text_from_page(page, render_page_image(page)))
        detected = detect_batch_title(header_samples, instruments)
        if detected:
            batch_title = detected
        elif batch_title and not is_acceptable_title(batch_title, instruments=instruments):
            batch_title = None

    for pdf_path in sorted(pdf_paths, key=lambda path: path.name.lower()):
        with fitz.open(pdf_path) as doc:
            if doc.page_count == 0:
                continue
            page = doc.load_page(0)
            page_image = render_page_image(page)
            header_text = extract_header_text_from_page(page, page_image)
            label_text = pick_instrument_label_text(header_text, instruments)
            if auto_detect_title:
                file_title = batch_title or extract_work_title_from_header(header_text, instruments) or ""
            else:
                file_title = (score_title or "").strip()

        if not file_title:
            file_title = "Unbenannt"

        match = match_instrument(label_text, instruments)
        clef = detect_clef(label_text, image=page_image)

        if match:
            tuning = tuning_for_filename(
                match.standard_tuning,
                match.detected_tuning,
                include_when_known=naming.include_tuning_when_known,
            )
            key = _count_key(instrument=match.name, tuning=tuning, clef=clef)
            instrument_counts[key] += 1
            number = instrument_counts[key]
            voice = VoiceParts(
                instrument=match.name,
                tuning=tuning,
                clef=clef,
                number=number,
                title=file_title,
            )
            prefix_parts = [match.name]
            if tuning:
                prefix_parts.append(tuning)
            if clef:
                prefix_parts.append(clef)
            prefix_parts.append(str(number))
            prefix = "_".join(prefix_parts)
            instrument_label = match.name
        else:
            unknown_count += 1
            number = unknown_count
            voice = VoiceParts(number=number, title=file_title, is_unknown=True)
            prefix = f"unknown_{number}"
            instrument_label = None

        output_name = build_output_name(voice, settings=naming, extension=pdf_path.suffix or ".pdf")
        destination = unique_destination(output_dir / output_name)

        if in_place:
            if pdf_path.resolve() != destination.resolve():
                shutil.move(pdf_path, destination)
        else:
            shutil.copy2(pdf_path, destination)

        results.append(
            RenameResult(
                source=pdf_path,
                destination=destination,
                instrument=instrument_label,
                prefix=prefix,
                title=file_title,
            )
        )

    return results


def process_directory(
    input_dir: Path,
    score_title: str | None,
    *,
    output_dir: Path | None = None,
    instruments: list[Instrument] | None = None,
    naming: NamingSettings | None = None,
    auto_detect_title: bool = False,
) -> list[RenameResult]:
    pdf_paths = list_pdfs_in_directory(input_dir)
    target_dir = output_dir or input_dir
    in_place = target_dir.resolve() == input_dir.resolve()
    return process_pdfs(
        pdf_paths,
        target_dir,
        score_title,
        instruments=instruments,
        naming=naming,
        in_place=in_place,
        auto_detect_title=auto_detect_title,
    )
