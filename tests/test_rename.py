from pathlib import Path
from unittest.mock import MagicMock, patch

from ocr_score_rename.instruments import Instrument, MatchResult
from ocr_score_rename.naming import NamingSettings
from ocr_score_rename.rename import process_pdfs


def _mock_pdf_doc() -> MagicMock:
    doc = MagicMock()
    doc.page_count = 1
    doc.load_page.return_value = MagicMock()
    doc.__enter__.return_value = doc
    doc.__exit__.return_value = False
    return doc


def test_process_pdfs_numbers_duplicate_instruments(tmp_path: Path):
    pdfs = []
    for index in range(2):
        pdf = tmp_path / f"scan_{index}.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        pdfs.append(pdf)

    instruments = [Instrument("Bariton", "B", ("Bariton",))]
    match = MatchResult(name="Bariton", standard_tuning="B", detected_tuning="B")

    with patch("ocr_score_rename.rename.fitz.open", return_value=_mock_pdf_doc()):
        with patch("ocr_score_rename.rename.render_page_image", return_value=object()):
            with patch("ocr_score_rename.rename.extract_header_text_from_page", return_value="Bariton in B"):
                with patch("ocr_score_rename.rename.match_instrument", return_value=match):
                    with patch("ocr_score_rename.rename.detect_clef", return_value=None):
                        results = process_pdfs(
                            pdfs,
                            tmp_path,
                            "Marsch",
                            instruments=instruments,
                            naming=NamingSettings(include_tuning_when_known=False),
                            in_place=True,
                        )

    names = sorted(result.destination.name for result in results)
    assert names == ["Bariton_1_Marsch.pdf", "Bariton_2_Marsch.pdf"]


def test_process_pdfs_separates_duplicate_by_clef(tmp_path: Path):
    pdfs = []
    for index in range(2):
        pdf = tmp_path / f"scan_{index}.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        pdfs.append(pdf)

    instruments = [Instrument("Bariton", "B", ("Bariton",))]
    match = MatchResult(name="Bariton", standard_tuning="B", detected_tuning="B")

    with patch("ocr_score_rename.rename.fitz.open", return_value=_mock_pdf_doc()):
        with patch("ocr_score_rename.rename.render_page_image", return_value=object()):
            with patch("ocr_score_rename.rename.extract_header_text_from_page", return_value="Bariton in B"):
                with patch("ocr_score_rename.rename.match_instrument", return_value=match):
                    with patch("ocr_score_rename.rename.detect_clef", side_effect=["VSl", "BSl"]):
                        results = process_pdfs(
                            pdfs,
                            tmp_path,
                            "Marsch",
                            instruments=instruments,
                            naming=NamingSettings(include_tuning_when_known=False),
                            in_place=True,
                        )

    names = sorted(result.destination.name for result in results)
    assert names == ["Bariton_BSl_1_Marsch.pdf", "Bariton_VSl_1_Marsch.pdf"]
