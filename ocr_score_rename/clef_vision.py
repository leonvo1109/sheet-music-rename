from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

MATCH_THRESHOLD = 0.38
DOT_PAIR_THRESHOLD = 0.85
SCALES = (0.55, 0.75, 1.0, 1.25, 1.55, 1.85)


def _build_templates() -> dict[str, np.ndarray]:
    bass = np.zeros((90, 56), dtype=np.uint8)
    cv2.circle(bass, (42, 52), 6, 255, -1)
    cv2.circle(bass, (42, 68), 6, 255, -1)
    cv2.ellipse(bass, (24, 60), (20, 30), 0, -100, 210, 255, 4)
    cv2.line(bass, (10, 24), (10, 86), 255, 3)

    treble = np.zeros((110, 58), dtype=np.uint8)
    cv2.ellipse(treble, (34, 78), (9, 9), 0, 0, 360, 255, 2)
    cv2.ellipse(treble, (30, 58), (18, 24), 0, 40, 320, 255, 3)
    cv2.line(treble, (18, 18), (18, 98), 255, 2)
    cv2.ellipse(treble, (24, 34), (10, 8), 0, 200, 340, 255, 2)

    return {"BSl": bass, "VSl": treble}


_TEMPLATES = _build_templates()


def _prepare_roi(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    height, width = gray.shape
    gray_roi = gray[0 : int(height * 0.55), 0 : int(width * 0.4)]
    if gray_roi.size == 0:
        return gray_roi, gray_roi
    binary_roi = cv2.adaptiveThreshold(
        gray_roi,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        11,
    )
    return gray_roi, binary_roi


def _best_template_score(roi: np.ndarray, template: np.ndarray) -> float:
    best = 0.0
    template_h, template_w = template.shape
    for scale in SCALES:
        scaled_w = max(8, int(template_w * scale))
        scaled_h = max(8, int(template_h * scale))
        if scaled_h >= roi.shape[0] or scaled_w >= roi.shape[1]:
            continue
        scaled = cv2.resize(template, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
        result = cv2.matchTemplate(roi, scaled, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        best = max(best, float(max_val))
    return best


def _has_treble_stem(binary_roi: np.ndarray) -> bool:
    num_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(binary_roi, connectivity=8)
    min_height = binary_roi.shape[0] * 0.5
    for label in range(1, num_labels):
        width = stats[label, cv2.CC_STAT_WIDTH]
        height = stats[label, cv2.CC_STAT_HEIGHT]
        x_pos = stats[label, cv2.CC_STAT_LEFT]
        if width <= 8 and height >= min_height and x_pos <= binary_roi.shape[1] * 0.25:
            return True
    return False


def _bass_dot_pair_score(gray_roi: np.ndarray, binary_roi: np.ndarray) -> float:
    """Detect the two dots that are characteristic of the F-clef."""
    blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=8,
        param1=70,
        param2=12,
        minRadius=3,
        maxRadius=16,
    )
    dot_candidates: list[tuple[float, float, int]] = []
    min_x = binary_roi.shape[1] * 0.38
    max_x = binary_roi.shape[1] * 0.72

    if circles is not None:
        for x_pos, y_pos, radius in np.round(circles[0]).astype(int):
            if min_x <= x_pos <= max_x:
                dot_candidates.append((float(x_pos), float(y_pos), int(radius)))

    if len(dot_candidates) < 2:
        return 0.0

    best = 0.0
    for index, (x1, y1, r1) in enumerate(dot_candidates):
        for x2, y2, r2 in dot_candidates[index + 1 :]:
            if abs(x1 - x2) > 18 or abs(r1 - r2) > 6:
                continue
            if 10 <= abs(y1 - y2) <= 44:
                best = max(best, 0.92)
    return best


def detect_clef_from_image(image: Image.Image) -> tuple[str | None, float]:
    """Return clef code and confidence from the rendered page image."""
    gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    gray_roi, binary_roi = _prepare_roi(gray)
    if binary_roi.size == 0:
        return None, 0.0

    if _has_treble_stem(binary_roi):
        return "VSl", 0.9

    bass_dots = _bass_dot_pair_score(gray_roi, binary_roi)
    if bass_dots >= DOT_PAIR_THRESHOLD:
        return "BSl", bass_dots

    template_scores = {
        code: _best_template_score(binary_roi, template) for code, template in _TEMPLATES.items()
    }
    best_code = max(template_scores, key=template_scores.get)
    best_score = template_scores[best_code]
    second_score = sorted(template_scores.values(), reverse=True)[1]

    if best_score < MATCH_THRESHOLD:
        return None, best_score
    if best_score - second_score < 0.04:
        return None, best_score
    return best_code, best_score


def detect_clef_code_from_image(image: Image.Image) -> str | None:
    code, _confidence = detect_clef_from_image(image)
    return code
