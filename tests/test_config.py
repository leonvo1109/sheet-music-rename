from ocr_score_rename.config import instruments_to_yaml_data, load_instruments_from_file, save_instruments
from ocr_score_rename.instruments import Instrument, parse_instruments


def test_parse_instruments_adds_name_as_synonym():
    instruments = parse_instruments(
        {"instruments": [{"name": "Geige", "tuning": "C", "synonyms": ["violine", "vln"]}]}
    )
    assert instruments[0].name == "Geige"
    assert instruments[0].tuning == "C"
    assert instruments[0].synonyms == ("Geige", "violine", "vln")


def test_save_and_load_roundtrip(tmp_path):
    instruments = [
        Instrument("Klarinette", "B", ("Klarinette", "clarinet")),
        Instrument("Flöte", "C", ("Flöte", "fl.", "flute")),
    ]
    path = tmp_path / "instruments.yaml"
    save_instruments(instruments, path=path)
    loaded = load_instruments_from_file(path)
    assert loaded == instruments


def test_instruments_to_yaml_data_deduplicates_name():
    instruments = [Instrument("Horn", "F", ("Horn", "waldhorn"))]
    data = instruments_to_yaml_data(instruments)
    assert data["instruments"][0] == {"name": "Horn", "tuning": "F", "synonyms": ["waldhorn"]}
