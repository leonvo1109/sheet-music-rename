import sys
from pathlib import Path

from ocr_score_rename import tesseract_runtime


def test_bundle_root_when_frozen(tmp_path: Path, monkeypatch):
    tess_dir = tmp_path / "tesseract"
    tess_dir.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert tesseract_runtime.bundle_root() == tess_dir


def test_configure_uses_bundled_windows_binary(tmp_path: Path, monkeypatch):
    bundle = tmp_path / "tesseract"
    tessdata = bundle / "tessdata"
    tessdata.mkdir(parents=True)
    exe = bundle / "tesseract.exe"
    exe.write_text("stub", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "platform", "win32")

    tesseract_runtime.configure_tesseract()

    assert tesseract_runtime.pytesseract.pytesseract.tesseract_cmd == str(exe)
    assert tesseract_runtime.os.environ["TESSDATA_PREFIX"] == str(tessdata)
