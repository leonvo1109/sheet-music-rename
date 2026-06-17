# OCR Score Rename

Copy scanned PDF score parts into an output folder with consistent filenames. The app OCRs the first page of each PDF, detects the instrument from a synonym list, and renames files as:

- **Matched:** `{instrument}{nr}_{score_title}.pdf` — e.g. `violin1_Beethoven 5.pdf`
- **Unmatched:** `unknown_{nr}_{score_title}.pdf` — e.g. `unknown_1_Mystery Score.pdf`

Instrument counters are per type (`violin1`, `violin2`, …; `unknown_1`, `unknown_2`, …).

## Für Endnutzer (ohne Installation)

Die **CI-Builds** (macOS/Windows) enthalten Tesseract bereits im Paket. Es sind **keine Admin-Rechte** und keine separate Tesseract-Installation nötig.

1. ZIP-Release-Asset herunterladen (bei Release-Tags `v*` öffentlich verfügbar).
2. Ordner entpacken, z. B. nach `OCR Score Rename`.
3. **Windows:** Rechtsklick auf `ocr-score-rename.exe` → „Verknüpfung erstellen“ → Verknüpfung auf den Desktop ziehen.
4. **macOS:** Doppelklick auf `ocr-score-rename` (ggf. einmalig in den Systemeinstellungen „Öffnen“ bestätigen).

Der gesamte Ordner muss erhalten bleiben — nicht nur die `.exe`/das Binary kopieren.

## Requirements (nur Entwicklung)

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) auf dem Entwicklungsrechner (für `pytest` und lokale Läufe ohne Bundle)

## Run from source

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m ocr_score_rename
```

Or use the console script:

```bash
ocr-score-rename
```

## GUI

1. Enter the **score title** (used in every output filename).
2. Choose an **output folder**.
3. **Add PDFs** — select one or more scanned parts.
4. Click **Rename & copy**.

## Custom instruments

Edit `ocr_score_rename/data/instruments.yaml` to add instruments and OCR synonyms (German and English abbreviations are included by default).

## Build a standalone executable (with bundled Tesseract)

Tesseract wird beim Build in das Programm eingepackt — Endnutzer brauchen nichts zusätzlich zu installieren.

```bash
pip install -e ".[build]"

# Tesseract muss auf dem Build-Rechner installiert sein (einmalig, z. B. brew/choco):
#   macOS:   brew install tesseract dylibbundler
#   Windows: choco install tesseract

python scripts/stage_tesseract.py
pyinstaller ocr-score-rename.spec
```

Output: `dist/ocr-score-rename/` — diesen Ordner als ZIP verteilen.

## CI builds

GitHub Actions (`.github/workflows/build.yml`) runs on tagged releases (`v*`) or manually via **workflow_dispatch**:

- **macOS** and **Windows** — PyInstaller builds with bundled Tesseract; for tags (`v*`) ZIPs are also published as public release assets.
- **Ubuntu** — pytest (system Tesseract for tests only).

For public downloads, use the release assets on the corresponding tag.

## Project layout

```
ocr-score-rename/
├── .github/workflows/build.yml
├── scripts/stage_tesseract.py  # pack Tesseract for PyInstaller
├── ocr_score_rename/
│   ├── data/instruments.yaml
│   ├── gui.py
│   ├── instruments.py
│   ├── ocr.py
│   ├── rename.py
│   └── tesseract_runtime.py    # bundled vs system Tesseract
├── tests/
├── main.py
├── ocr-score-rename.spec
└── pyproject.toml
```
