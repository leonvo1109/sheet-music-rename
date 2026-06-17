from ocr_score_rename.instruments import Instrument
from ocr_score_rename.synonym_validation import validate_synonym
from ocr_score_rename.text_normalize import normalize_for_match, normalized_key


def test_normalize_for_match_folds_case_and_apostrophes():
    assert normalize_for_match("Cor d'Harmonie") == normalize_for_match("cor dharmonie")


def test_normalized_key_ignores_spaces_and_umlauts():
    assert normalized_key("Flöte") == normalized_key("floete")


def test_validate_synonym_rejects_duplicate_with_apostrophe_variant():
    instrument = Instrument("Horn", "F", ("Horn", "cor d'harmonie"))
    error = validate_synonym("cor dharmonie", instrument=instrument, all_instruments=[instrument])
    assert error is not None


def test_validate_synonym_rejects_cross_instrument_collision():
    instruments = [
        Instrument("Flöte", "C", ("Flöte", "fl.")),
        Instrument("Oboe", "C", ("Oboe", "ob.")),
    ]
    error = validate_synonym("fl.", instrument=instruments[1], all_instruments=instruments)
    assert error is not None
