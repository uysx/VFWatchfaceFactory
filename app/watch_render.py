"""
Watch/time widget rendering: composes the hour/minute/second hand images and
rotates each around its own pivot (center) point, then positions the rotated
image so that pivot lands on the hand's anchor point on the watch face.

The clock hands rotate to the shared, user-editable preview time
(app.preview_data.PreviewData.hour/minute/second) rather than a single fixed
demo time, so the hands stay in sync with the same "9:30" (or whatever the
user has set) that every digit/letter widget on the face previews against.

Angle formulas and padding/rotation geometry are ported directly from the
reference C++ renderWatchHands():
    hour_angle   = (hour % 12 + minute / 60) * 30
    minute_angle = (minute + second / 60)    *  6
    second_angle = second                     *  6

For each hand:
    1. Build a symmetric square canvas centered on the hand image's pivot
       (center x/y) so rotation never clips the image.
    2. Rotate that canvas clockwise by the angle (Qt's QTransform.rotate()
       rotates clockwise for positive degrees on-screen, matching the
       reference behavior).
    3. Position the rotated canvas so its own center lands at the hand's
       anchor x/y (plus the watch widget's own x/y offset).

No text is drawn anywhere in this module.
"""
import os
from dataclasses import dataclass

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QImage, QPainter, QTransform, QColor

from .preview_data import PreviewData


@dataclass
class RenderedHand:
    image: QImage
    pos: QPointF


def _paste_centered_and_rotate(src: QImage, ox: int, oy: int, angle_deg: float) -> QImage:
    if src.isNull():
        return QImage()

    pad_l = max(ox, src.width() - ox)
    pad_t = max(oy, src.height() - oy)
    big_w = max(pad_l * 2, 1)
    big_h = max(pad_t * 2, 1)

    big = QImage(big_w, big_h, QImage.Format.Format_ARGB32_Premultiplied)
    big.fill(QColor(0, 0, 0, 0))
    p = QPainter(big)
    p.drawImage(pad_l - ox, pad_t - oy, src)
    p.end()

    transform = QTransform()
    transform.translate(big_w / 2.0, big_h / 2.0)
    transform.rotate(angle_deg)
    transform.translate(-big_w / 2.0, -big_h / 2.0)

    return big.transformed(transform, Qt.TransformationMode.SmoothTransformation)


def _load_hand_image(project_dir: str, filename: str) -> QImage:
    if not filename:
        return QImage()
    path = os.path.join(project_dir, filename)
    if not os.path.isfile(path):
        return QImage()
    img = QImage(path)
    if img.isNull():
        return img
    return img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)


def render_watch_hands(project_dir: str, watch_json: dict, preview: PreviewData = None):
    """
    Returns a dict {"hour": RenderedHand, "minute": RenderedHand, "second": RenderedHand}
    (omitting any hand whose source image could not be loaded).
    Positions are already shifted by the watch widget's own x/y offset.
    Hand angles are computed from `preview` (defaults to PreviewData()'s
    stock 09:30:00 if none is supplied).
    """
    if preview is None:
        preview = PreviewData()

    hour_angle = (preview.hour % 12 + preview.minute / 60.0) * 30.0
    min_angle = (preview.minute + preview.second / 60.0) * 6.0
    sec_angle = preview.second * 6.0

    wx = int(watch_json.get("x", 0) or 0)
    wy = int(watch_json.get("y", 0) or 0)

    specs = [
        ("hour", "hour", "hourcenterx", "hourcentery", "houranchorx", "houranchory", hour_angle),
        ("minute", "minute", "mincenterx", "mincentery", "minanchorx", "minanchory", min_angle),
        ("second", "second", "seccenterx", "seccentery", "secanchorx", "secanchory", sec_angle),
    ]

    results = {}
    for out_key, img_key, cx_key, cy_key, ax_key, ay_key, angle in specs:
        filename = watch_json.get(img_key, "")
        src = _load_hand_image(project_dir, filename)
        if src.isNull():
            continue

        ox = int(watch_json.get(cx_key, 0) or 0)
        oy = int(watch_json.get(cy_key, 0) or 0)
        ax = int(watch_json.get(ax_key, 0) or 0)
        ay = int(watch_json.get(ay_key, 0) or 0)

        rotated = _paste_centered_and_rotate(src, ox, oy, angle)
        if rotated.isNull():
            continue

        pos = QPointF(ax - rotated.width() / 2.0 + wx, ay - rotated.height() / 2.0 + wy)
        results[out_key] = RenderedHand(image=rotated, pos=pos)

    return results
