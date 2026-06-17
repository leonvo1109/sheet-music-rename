from ocr_score_rename.rename import build_output_name


def test_build_output_name_matched():
    assert build_output_name(
        instrument="Geige",
        number=2,
        score_title="Beethoven 5",
        extension=".pdf",
    ) == "Geige2_Beethoven 5.pdf"


def test_build_output_name_with_tuning():
    assert build_output_name(
        instrument="Klarinette",
        tuning="E",
        number=1,
        score_title="Marsch",
        extension=".pdf",
    ) == "Klarinette_E_1_Marsch.pdf"


def test_build_output_name_unknown():
    assert build_output_name(
        instrument=None,
        number=1,
        score_title="Mystery Score",
        extension=".pdf",
    ) == "unknown_1_Mystery Score.pdf"
