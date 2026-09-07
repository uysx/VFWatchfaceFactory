"""
Image-glyph rendering engine.

CORE RULE: nothing in this module ever draws text. Every widget value is
composed by looking up pre-made glyph images (by filename stem) out of an
in-memory "image strip" (dict[str, QImage]) and compositing them with
QPainter.drawImage(). Punctuation such as ':' is never drawn as a character -
it is resolved to a glyph filename (conventionally "10") exactly like any
digit, exactly as the source font provides it.

Two families of custom widgets:
  * "digit" widgets (time, date, week is NOT digit - see letter widgets)
    render a string of characters by looking up one glyph image per
    character and compositing them left-to-right (or wrapped, depending on
    alignment), matching the reference editor's renderCustomWidgetImage().
  * "letter" widgets (week, month, apm) look up a single named image
    directly, e.g. "en_wed.png".
  * "icon" / "anima" / "redpoint" widgets show a single static image.
"""
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPainter

from . import widget_registry as reg


def _glyph_key_for_char(ch: str) -> str:
    """Map a preview-value character to the glyph filename stem to look up."""
    if ch.isdigit():
        return ch
    if ch in reg.WEATHER_UNIT_GLYPH:
        return reg.WEATHER_UNIT_GLYPH[ch]
    if ch in reg.SPECIAL_CHAR_GLYPH:
        return reg.SPECIAL_CHAR_GLYPH[ch]
    return ""


def _preview_value_for(type_value: str, json_obj: dict) -> str:
    if type_value == "battery":
        fontnum = int(json_obj.get("fontnum", 11) or 0)
        return "100" if fontnum <= 10 else "100%"
    if type_value == "weather":
        style = int(json_obj.get("style", 2) or 2)
        base = reg.DIGIT_PREVIEW.get(type_value, "0")
        suffix = reg.WEATHER_UNIT_SENTINEL_C if style == 2 else reg.WEATHER_UNIT_SENTINEL_F
        return base + suffix
    return reg.DIGIT_PREVIEW.get(type_value, "0")


def _lookup_glyph(strip: dict, key: str):
    if not key:
        return None
    img = strip.get(key)
    if img is not None and not img.isNull():
        return img
    return None


def _collect_glyphs(strip: dict, value: str):
    """Return list of QImage glyphs (in order) for a preview value string."""
    glyphs = []
    for ch in value:
        key = _glyph_key_for_char(ch)
        img = _lookup_glyph(strip, key)
        if img is not None:
            glyphs.append(img)
    return glyphs


def _compose_row(glyphs, canvas_w: int, align: str) -> QImage:
    """Compose a single row of glyphs into one QImage, honoring alignment."""
    total_w = sum(g.width() for g in glyphs)
    max_h = max((g.height() for g in glyphs), default=0)
    row_w = max(total_w, canvas_w if canvas_w > 0 else 0)
    if row_w <= 0:
        row_w = total_w

    if align == "center":
        x = (row_w - total_w) // 2
    elif align == "right":
        x = row_w - total_w
    else:  # left / autowrap-row
        x = 0

    result = QImage(max(row_w, 1), max(max_h, 1), QImage.Format.Format_ARGB32_Premultiplied)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    for g in glyphs:
        painter.drawImage(x, 0, g)
        x += g.width()
    painter.end()
    return result


def _compose_autowrap(glyphs, canvas_w: int) -> QImage:
    """Wrap glyphs onto multiple rows once a row would exceed canvas_w."""
    if canvas_w <= 0:
        return _compose_row(glyphs, canvas_w, "left")

    rows = []
    current = []
    current_w = 0
    for g in glyphs:
        if current and current_w + g.width() > canvas_w:
            rows.append(current)
            current = []
            current_w = 0
        current.append(g)
        current_w += g.width()
    if current:
        rows.append(current)

    row_images = [_compose_row(r, canvas_w, "left") for r in rows]
    total_h = sum(r.height() for r in row_images)
    max_w = max((r.width() for r in row_images), default=canvas_w)
    result = QImage(max(max_w, 1), max(total_h, 1), QImage.Format.Format_ARGB32_Premultiplied)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    y = 0
    for r in row_images:
        painter.drawImage(0, y, r)
        y += r.height()
    painter.end()
    return result


def render_digit_widget(strip: dict, type_value: str, json_obj: dict) -> QImage:
    value = _preview_value_for(type_value, json_obj)
    glyphs = _collect_glyphs(strip, value)
    if not glyphs:
        return QImage()

    align = json_obj.get("align", "left")
    canvas_w = int(json_obj.get("w", 0) or 0)

    if align == "autowrap":
        return _compose_autowrap(glyphs, canvas_w)
    return _compose_row(glyphs, canvas_w, align)


def render_letter_widget(strip: dict, type_value: str) -> QImage:
    key = reg.LETTER_PREVIEW.get(type_value, "")
    img = _lookup_glyph(strip, key)
    if img is not None:
        return img
    if strip:
        return next(iter(strip.values()))
    return QImage()


def render_static_single_image(strip: dict, key: str) -> QImage:
    img = _lookup_glyph(strip, key)
    if img is not None:
        return img
    if strip:
        return next(iter(strip.values()))
    return QImage()


def render_custom_widget_image(type_value: str, strip: dict, json_obj: dict) -> QImage:
    """Dispatch to the correct pure-image renderer for a custom/* widget."""
    if type_value == "anima":
        return render_static_single_image(strip, "0")
    if type_value == "icon":
        return render_static_single_image(strip, "__icon__")
    if type_value == "redpoint":
        return render_static_single_image(strip, "0")
    if type_value in reg.LETTER_TYPES:
        return render_letter_widget(strip, type_value)
    return render_digit_widget(strip, type_value, json_obj)


def measure_custom_widget(type_value: str, strip: dict, json_obj: dict) -> QSize:
    img = render_custom_widget_image(type_value, strip, json_obj)
    if img.isNull():
        return QSize(50, 20)
    return img.size()
