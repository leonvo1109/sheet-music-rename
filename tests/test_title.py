from ocr_score_rename.instruments import Instrument
from ocr_score_rename.title import (
    _is_noise_line,
    _pick_best_line,
    extract_work_title_from_header,
    is_acceptable_title,
)


def test_pick_best_line_returns_single_title():
    instruments = [Instrument("Bariton", "B", ("Bariton", "bar."))]
    candidates = [
        (12.0, 40.0, 20.0, "Bariton 1"),
        (28.0, 30.0, 15.0, "Bayerischer Defiliermarsch"),
        (27.0, 48.0, 15.0, "Johann Strauß"),
        (26.0, 52.0, 15.0, "in B"),
    ]
    terms = {"bariton", "bar"}
    assert _pick_best_line(candidates, terms) == "Bayerischer Defiliermarsch"


def test_noise_line_rejects_voice_and_instrument_labels():
    terms = {"bariton", "trompete"}
    assert _is_noise_line("Bariton 1", terms)
    assert _is_noise_line("Trompete in B", terms)
    assert _is_noise_line("Stimme 2", terms)
    assert not _is_noise_line("Bayerischer Defiliermarsch", terms)


def test_extract_work_title_from_combined_instrument_line():
    instruments = [Instrument("Tenorhorn", "B", ("Tenorhorn",))]
    header = "3.Tenorhorn in BO In Harmonie verein\narsch"
    assert extract_work_title_from_header(header, instruments) == "In Harmonie verein"


def test_extract_work_title_from_header_blasorchester_layout():
    instruments = [Instrument("Horn", "F", ("Horn", "waldhorn"))]
    header = "In Harmonie verein\n\n>\n\nmf\n\n1.Horn in F\n"
    assert extract_work_title_from_header(header, instruments) == "In Harmonie verein"


def test_extract_work_title_joins_title_and_subtitle():
    instruments = [Instrument("Oboe", "C", ("Oboe",))]
    header = "In Harmonie verein\nMarsch\n\nOboe\n"
    assert extract_work_title_from_header(header, instruments) == "In Harmonie verein Marsch"


def test_is_acceptable_title_rejects_ocr_garbage():
    assert not is_acceptable_title("arscl")
    assert not is_acceptable_title("mf")
    assert is_acceptable_title("In Harmonie verein Marsch")
