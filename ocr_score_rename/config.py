from __future__ import annotations

import os
import shutil
import sys
from importlib import resources
from pathlib import Path

import yaml

from ocr_score_rename.instruments import Instrument, parse_instruments
from ocr_score_rename.text_normalize import normalized_key


def user_config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "ocr-score-rename"


def instruments_config_path() -> Path:
    return user_config_dir() / "instruments.yaml"


def bundled_instruments_path() -> Path:
    return Path(str(resources.files("ocr_score_rename.data") / "instruments.yaml"))


def ensure_user_config() -> Path:
    path = instruments_config_path()
    if path.is_file():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bundled_instruments_path(), path)
    return path


def load_instruments_from_file(path: Path) -> list[Instrument]:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parse_instruments(parsed)


def load_instruments() -> list[Instrument]:
    return load_instruments_from_file(ensure_user_config())


def load_default_instruments() -> list[Instrument]:
    return load_instruments_from_file(bundled_instruments_path())


def instruments_to_yaml_data(instruments: list[Instrument]) -> dict:
    entries = []
    for instrument in instruments:
        extra_synonyms = [s for s in instrument.synonyms if normalized_key(s) != normalized_key(instrument.name)]
        entry: dict[str, object] = {"name": instrument.name, "synonyms": extra_synonyms}
        if instrument.tuning:
            entry["tuning"] = instrument.tuning
        entries.append(entry)
    return {"instruments": entries}


def save_instruments(instruments: list[Instrument], path: Path | None = None) -> Path:
    target = path or instruments_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = instruments_to_yaml_data(instruments)
    target.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return target


def reset_instruments_to_default() -> list[Instrument]:
    defaults = load_default_instruments()
    save_instruments(defaults)
    return defaults
