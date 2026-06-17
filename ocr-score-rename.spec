# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ocr-score-rename (onedir + bundled Tesseract)."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
project_root = Path(SPECPATH)
tesseract_bundle = project_root / "build" / "tesseract_bundle"

datas = collect_data_files("ocr_score_rename", includes=["**/data/*"])
binaries: list[tuple[str, str]] = []

if tesseract_bundle.is_dir():
    if sys.platform == "win32":
        for item in tesseract_bundle.rglob("*"):
            if not item.is_file():
                continue
            rel = item.relative_to(tesseract_bundle)
            dest = Path("tesseract") / rel.parent
            entry = (str(item), str(dest))
            if item.suffix.lower() in {".exe", ".dll"}:
                binaries.append(entry)
            else:
                datas.append(entry)
    else:
        for item in (tesseract_bundle / "bin").glob("*"):
            if item.is_file():
                binaries.append((str(item), "tesseract/bin"))
        for item in (tesseract_bundle / "lib").glob("*"):
            if item.is_file():
                binaries.append((str(item), "tesseract/lib"))
        for item in (tesseract_bundle / "tessdata").glob("*.traineddata"):
            datas.append((str(item), "tesseract/tessdata"))

a = Analysis(
    ["ocr_score_rename/__main__.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "ocr_score_rename.gui",
        "ocr_score_rename.rename",
        "ocr_score_rename.ocr",
        "ocr_score_rename.clef",
        "ocr_score_rename.clef_vision",
        "ocr_score_rename.page_regions",
        "ocr_score_rename.instruments",
        "ocr_score_rename.config",
        "ocr_score_rename.config_dialog",
        "ocr_score_rename.tesseract_runtime",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ocr-score-rename",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ocr-score-rename",
)
