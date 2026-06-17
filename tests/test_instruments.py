from ocr_score_rename.instruments import Instrument, match_instrument, pick_instrument_label_text, tuning_for_filename, tuning_suffix


def test_match_instrument_case_insensitive():
    instruments = [Instrument("Flügelhorn", "B", ("Flügelhorn", "flh.", "flugelhorn"))]
    assert match_instrument("FLÜGELHORN in B", instruments).name == "Flügelhorn"


def test_match_instrument_apostrophe_variants():
    instruments = [Instrument("Horn", "F", ("Horn", "cor d'harmonie", "waldhorn"))]
    assert match_instrument("Cor d'harmonie", instruments).name == "Horn"
    assert match_instrument("Cor dharmonie", instruments).name == "Horn"


def test_match_instrument_multilingual_synonym():
    instruments = [Instrument("Posaune", "B", ("Posaune", "trombone", "pos."))]
    assert match_instrument("TROMBONE 2", instruments).name == "Posaune"


def test_match_instrument_prefers_longer_synonym():
    instruments = [
        Instrument("Saxophon", "", ("Saxophon", "sax")),
        Instrument("Tenorsaxophon", "B", ("Tenorsaxophon", "tenor saxophone", "tenorsax")),
    ]
    assert match_instrument("Tenor Saxophone 1", instruments).name == "Tenorsaxophon"


def test_match_instrument_detects_nonstandard_tuning():
    instruments = [Instrument("Klarinette", "B", ("Klarinette", "clarinet", "klarinette in es"))]
    result = match_instrument("Klarinette in Es 2", instruments)
    assert result.name == "Klarinette"
    assert tuning_suffix(result.standard_tuning, result.detected_tuning) == "E"


def test_match_instrument_standard_tuning_has_no_suffix():
    instruments = [Instrument("Klarinette", "B", ("Klarinette", "clarinet"))]
    result = match_instrument("Klarinette in B 1", instruments)
    assert tuning_suffix(result.standard_tuning, result.detected_tuning) is None
    assert tuning_for_filename(result.standard_tuning, result.detected_tuning, include_when_known=True) == "B"


def test_match_instrument_ignores_short_false_synonyms():
    instruments = [
        Instrument("Posaune", "B", ("Posaune", "pos.", "in")),
        Instrument("Bariton", "B", ("Bariton",)),
    ]
    assert match_instrument("in b dur marsch", instruments) is None


def test_pick_instrument_label_prefers_numbered_part_line():
    instruments = [
        Instrument("Posaune", "B", ("Posaune", "trombone")),
        Instrument("Bariton", "B", ("Bariton",)),
    ]
    header = "1 Posaune in BP In Harmonie verein\nMarsch\n(ist Trombone Sib)"
    assert pick_instrument_label_text(header, instruments) == "1 Posaune in BP In Harmonie verein"


def test_pick_instrument_label_prefers_short_matching_line():
    instruments = [
        Instrument("Bariton", "B", ("Bariton",)),
        Instrument("Trompete", "B", ("Trompete",)),
    ]
    header = "Bayerischer Defiliermarsch\nBariton in B 1\nAllegro maestoso"
    assert pick_instrument_label_text(header, instruments) == "Bariton in B 1"


def test_match_instrument_percussion_english():
    instruments = [Instrument("Schlagzeug", "", ("Schlagzeug", "percussion", "percussion 1", "perc."))]
    assert match_instrument("Percussion 2", instruments).name == "Schlagzeug"
