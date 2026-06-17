#!/usr/bin/env python3
"""Stage a self-contained Tesseract folder for PyInstaller bundling."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

BUNDLE_ROOT = Path("build/tesseract_bundle")
# eng + deu cover typical score part labels; osd helps page orientation detection.
TESSDATA_LANGS = ("eng", "deu", "osd")


def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def _copy_tessdata(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for lang in TESSDATA_LANGS:
        trained = source / f"{lang}.traineddata"
        if not trained.is_file():
            raise SystemExit(f"Missing tessdata file: {trained}")
        shutil.copy2(trained, destination / trained.name)


def stage_windows(source: Path | None = None) -> Path:
    src = source or Path(r"C:\Program Files\Tesseract-OCR")
    if not src.is_dir():
        raise SystemExit(f"Tesseract not found at {src}. Install it before building.")

    dst = BUNDLE_ROOT
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    for pattern in ("*.exe", "*.dll"):
        for item in src.glob(pattern):
            shutil.copy2(item, dst / item.name)

    _copy_tessdata(src / "tessdata", dst / "tessdata")
    return dst


def _otool_libraries(binary: Path) -> list[Path]:
    output = subprocess.check_output(["otool", "-L", str(binary)], text=True)
    libs: list[Path] = []
    for line in output.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        match = re.match(r"\s+(\S+)", line)
        if not match:
            continue
        lib = Path(match.group(1))
        if str(lib).startswith(("/usr/lib", "/System")):
            continue
        libs.append(lib)
    return libs


def _bundle_macos_with_dylibbundler(tess_bin: Path, bin_dir: Path, lib_dir: Path) -> None:
    bundled = bin_dir / "tesseract"
    shutil.copy2(tess_bin, bundled)
    bundled.chmod(0o755)
    subprocess.run(
        [
            "dylibbundler",
            "-of",
            "-b",
            "-x",
            str(bundled),
            "-d",
            str(lib_dir) + "/",
            "-p",
            "@executable_path/../lib/",
        ],
        check=True,
    )


def _bundle_macos_manual(tess_bin: Path, bin_dir: Path, lib_dir: Path) -> None:
    bundled = bin_dir / "tesseract"
    shutil.copy2(tess_bin, bundled)
    bundled.chmod(0o755)

    queue = [bundled]
    copied: dict[Path, Path] = {}

    while queue:
        binary = queue.pop()
        for lib_path in _otool_libraries(binary):
            if lib_path in copied or not lib_path.is_file():
                continue
            dest = lib_dir / lib_path.name
            shutil.copy2(lib_path, dest)
            copied[lib_path] = dest
            queue.append(dest)

    for bundled_lib in copied.values():
        subprocess.run(
            ["install_name_tool", "-id", f"@rpath/{bundled_lib.name}", str(bundled_lib)],
            check=False,
        )

    subprocess.run(
        ["install_name_tool", "-add_rpath", "@executable_path/../lib", str(bundled)],
        check=False,
    )

    for original, bundled_lib in copied.items():
        for target in (bundled, *copied.values()):
            subprocess.run(
                [
                    "install_name_tool",
                    "-change",
                    str(original),
                    f"@rpath/{bundled_lib.name}",
                    str(target),
                ],
                check=False,
            )


def stage_macos() -> Path:
    brew_prefix = Path(_run(["brew", "--prefix"]))
    tess_bin = brew_prefix / "bin" / "tesseract"
    tessdata = brew_prefix / "share" / "tessdata"

    if not tess_bin.is_file():
        raise SystemExit(f"Tesseract not found at {tess_bin}. Run: brew install tesseract")

    dst = BUNDLE_ROOT
    if dst.exists():
        shutil.rmtree(dst)

    bin_dir = dst / "bin"
    lib_dir = dst / "lib"
    bin_dir.mkdir(parents=True)
    lib_dir.mkdir(parents=True)
    _copy_tessdata(tessdata, dst / "tessdata")

    if shutil.which("dylibbundler"):
        _bundle_macos_with_dylibbundler(tess_bin, bin_dir, lib_dir)
    else:
        _bundle_macos_manual(tess_bin, bin_dir, lib_dir)

    return dst


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    if sys.platform == "win32":
        bundle = stage_windows()
    elif sys.platform == "darwin":
        bundle = stage_macos()
    else:
        print("Linux builds use system Tesseract; skipping bundle staging.", file=sys.stderr)
        return

    print(f"Staged Tesseract at {bundle.resolve()}")


if __name__ == "__main__":
    main()
