from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytesseract


def bundle_root() -> Path | None:
    """Return the bundled Tesseract directory when running as a PyInstaller app."""
    if not getattr(sys, "frozen", False):
        return None
    root = Path(sys._MEIPASS) / "tesseract"
    return root if root.is_dir() else None


def configure_tesseract() -> None:
    """Use bundled Tesseract in frozen builds; fall back to a system install in dev."""
    bundled = bundle_root()
    if bundled is not None:
        if sys.platform == "win32":
            cmd = bundled / "tesseract.exe"
            tessdata = bundled / "tessdata"
        else:
            cmd = bundled / "bin" / "tesseract"
            tessdata = bundled / "tessdata"

        if cmd.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(cmd)
            os.environ["TESSDATA_PREFIX"] = str(tessdata)
            return

    if shutil.which("tesseract"):
        return

    candidates: list[Path] = []
    if sys.platform == "darwin":
        candidates = [
            Path("/opt/homebrew/bin/tesseract"),
            Path("/usr/local/bin/tesseract"),
        ]
    elif sys.platform == "win32":
        candidates = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ]

    for candidate in candidates:
        if candidate.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return
