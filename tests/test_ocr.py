from ocr_score_rename.ocr import embedded_text_sufficient


def test_embedded_text_sufficient_with_digital_score_header():
    text = "Flügelhorn in B\nMarsch der freiwilligen Feuerwehr"
    assert embedded_text_sufficient(text)


def test_embedded_text_sufficient_rejects_empty_scan():
    assert not embedded_text_sufficient("")
    assert not embedded_text_sufficient("   \n  ")


def test_embedded_text_sufficient_rejects_noise():
    assert not embedded_text_sufficient("123 456")
