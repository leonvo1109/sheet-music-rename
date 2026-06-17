from PIL import Image, ImageDraw

from ocr_score_rename.clef import detect_clef, detect_clef_from_text
from ocr_score_rename.clef_vision import detect_clef_code_from_image


def _draw_staff(draw: ImageDraw.ImageDraw, *, width: int = 280, top: int = 80, spacing: int = 12) -> None:
    for line in range(5):
        y = top + line * spacing
        draw.line((40, y, width, y), fill=0, width=2)


def _make_bass_clef_scan() -> Image.Image:
    image = Image.new("L", (360, 260), 255)
    draw = ImageDraw.Draw(image)
    _draw_staff(draw)
    draw.ellipse((70, 106, 88, 124), fill=0)
    draw.ellipse((70, 130, 88, 148), fill=0)
    draw.arc((46, 94, 94, 162), 250, 60, fill=0, width=5)
    draw.line((28, 78, 28, 170), fill=0, width=4)
    return image.convert("RGB")


def _make_treble_clef_scan() -> Image.Image:
    image = Image.new("L", (360, 260), 255)
    draw = ImageDraw.Draw(image)
    _draw_staff(draw)
    draw.line((34, 62, 34, 188), fill=0, width=3)
    draw.arc((52, 68, 108, 196), 15, 295, fill=0, width=5)
    draw.ellipse((66, 146, 84, 164), fill=0)
    draw.arc((44, 34, 88, 92), 200, 350, fill=0, width=3)
    return image.convert("RGB")


def test_detect_clef_from_text():
    assert detect_clef_from_text("Stimme: Bariton, Violinschlüssel")[0] == "VSl"
    assert detect_clef_from_text("Bariton, Bassschlüssel")[0] == "BSl"


def test_detect_clef_from_image_bass():
    assert detect_clef_code_from_image(_make_bass_clef_scan()) == "BSl"


def test_detect_clef_from_image_treble():
    assert detect_clef_code_from_image(_make_treble_clef_scan()) == "VSl"


def test_detect_clef_prefers_image_when_available():
    image = _make_bass_clef_scan()
    assert detect_clef("Violinschlüssel", image=image) == "BSl"


def test_detect_clef_falls_back_to_text_without_image():
    assert detect_clef("Bassschlüssel", image=None) == "BSl"
