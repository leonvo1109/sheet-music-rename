from __future__ import annotations

import os
import shutil
import sys
from importlib import resources
from pathlib import Path

import yaml

from ocr_score_rename.instruments import Instrument, parse_instruments
from ocr_score_rename.naming import FORMAT_PRESETS, DEFAULT_PARTS_ORDER, NamingSettings
from ocr_score_rename.text_normalize import normalized_key


def user_config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "ocr-score-rename"


def instruments_config_path() -> Path:
    return user_config_dir() / "instruments.yaml"


def settings_config_path() -> Path:
    return user_config_dir() / "settings.yaml"


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


def load_settings() -> NamingSettings:
    path = settings_config_path()
    if not path.is_file():
        return NamingSettings()

    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    preset = str(parsed.get("preset") or "Stimme – Nr – Titel")
    parts_order = FORMAT_PRESETS.get(preset, DEFAULT_PARTS_ORDER)
    custom_order = parsed.get("parts_order")
    if isinstance(custom_order, list) and custom_order:
        parts_order = tuple(str(part) for part in custom_order)

    return NamingSettings(
        separator=str(parsed.get("separator", "_")),
        parts_order=parts_order,
        include_tuning_when_known=bool(parsed.get("include_tuning_when_known", False)),
        preset=preset,
    )


def load_app_settings() -> dict:
    path = settings_config_path()
    if not path.is_file():
        return {"use_separate_output": False, "output_dir": "", "auto_detect_title": True}
    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "use_separate_output": bool(parsed.get("use_separate_output", False)),
        "output_dir": str(parsed.get("output_dir") or ""),
        "auto_detect_title": bool(parsed.get("auto_detect_title", True)),
    }


def save_settings(
    settings: NamingSettings,
    *,
    use_separate_output: bool = False,
    output_dir: str = "",
    auto_detect_title: bool = True,
) -> Path:
    path = settings_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "separator": settings.separator,
        "parts_order": list(settings.parts_order),
        "include_tuning_when_known": settings.include_tuning_when_known,
        "preset": settings.preset,
        "use_separate_output": use_separate_output,
        "output_dir": output_dir,
        "auto_detect_title": auto_detect_title,
    }
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
