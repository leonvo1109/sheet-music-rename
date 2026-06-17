from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_SEPARATOR = "_"
DEFAULT_PARTS_ORDER = ("instrument", "tuning", "clef", "number", "title")

FORMAT_PRESETS: dict[str, tuple[str, ...]] = {
    "Stimme – Nr – Titel": ("instrument", "tuning", "clef", "number", "title"),
    "Titel – Stimme – Nr": ("title", "instrument", "tuning", "clef", "number"),
    "Stimme – Titel – Nr": ("instrument", "tuning", "clef", "title", "number"),
    "Nr – Stimme – Titel": ("number", "instrument", "tuning", "clef", "title"),
}


@dataclass
class NamingSettings:
    separator: str = DEFAULT_SEPARATOR
    parts_order: tuple[str, ...] = DEFAULT_PARTS_ORDER
    include_tuning_when_known: bool = False
    preset: str = "Stimme – Nr – Titel"

    def normalized_separator(self) -> str:
        sep = self.separator
        if sep == "":
            return ""
        return re.sub(r'[<>:"/\\|?*]', "", sep)


@dataclass
class VoiceParts:
    instrument: str | None = None
    tuning: str | None = None
    clef: str | None = None
    number: int = 1
    title: str = ""
    is_unknown: bool = False


def _sanitize_filename_part(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", value.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def build_output_name(
    voice: VoiceParts,
    *,
    settings: NamingSettings,
    extension: str,
) -> str:
    sep = settings.normalized_separator()
    title = _sanitize_filename_part(voice.title)

    if voice.is_unknown:
        segments = ["unknown", str(voice.number), title]
        return sep.join(segment for segment in segments if segment) + extension

    values: dict[str, str] = {
        "title": title,
        "instrument": voice.instrument or "",
        "tuning": voice.tuning or "",
        "clef": voice.clef or "",
        "number": str(voice.number),
    }

    segments: list[str] = []
    for part in settings.parts_order:
        value = values.get(part, "")
        if not value:
            continue
        segments.append(value)

    if not segments:
        segments = ["unknown", str(voice.number), title]

    return sep.join(segments) + extension
