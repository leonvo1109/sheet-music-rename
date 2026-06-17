from ocr_score_rename.naming import NamingSettings, VoiceParts, build_output_name


def test_build_output_name_default_order():
    naming = NamingSettings(separator="_", include_tuning_when_known=True)
    result = build_output_name(
        VoiceParts(instrument="Klarinette", tuning="B", number=1, title="Marsch"),
        settings=naming,
        extension=".pdf",
    )
    assert result == "Klarinette_B_1_Marsch.pdf"


def test_build_output_name_title_first():
    naming = NamingSettings(
        separator="-",
        parts_order=("title", "instrument", "number"),
        include_tuning_when_known=False,
    )
    result = build_output_name(
        VoiceParts(instrument="Bariton", number=2, title="Polka"),
        settings=naming,
        extension=".pdf",
    )
    assert result == "Polka-Bariton-2.pdf"


def test_build_output_name_with_clef():
    naming = NamingSettings(include_tuning_when_known=True)
    result = build_output_name(
        VoiceParts(instrument="Bariton", tuning="B", clef="VSl", number=1, title="Marsch"),
        settings=naming,
        extension=".pdf",
    )
    assert result == "Bariton_B_VSl_1_Marsch.pdf"


def test_build_output_name_unknown():
    naming = NamingSettings()
    result = build_output_name(
        VoiceParts(number=1, title="Mystery", is_unknown=True),
        settings=naming,
        extension=".pdf",
    )
    assert result == "unknown_1_Mystery.pdf"
