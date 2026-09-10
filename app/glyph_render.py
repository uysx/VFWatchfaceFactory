"""
Image-glyph rendering engine.

CORE RULE: nothing in this module ever draws text. Every widget value is
composed by looking up pre-made glyph images (by filename stem) out of an
in-memory "image strip" (dict[str, QImage]) and compositing them with
QPainter.drawImage(). Punctuation such as ':' is never drawn as a character -
it is resolved to a glyph filename (conventionally "10") exactly like any
digit, exactly as the source font provides it.

Two families of custom widgets:
  * "digit" widgets (time, date, hour, min, second, calorie, distance, ...)
    render a string of characters by looking up one glyph image per
    character and compositing them left-to-right (or wrapped, depending on
    alignment). The character string itself is computed from a shared,
    user-editable PreviewData (app.preview_data) instead of one fixed demo
    value per type - so setting the preview clock to 9:30 makes the "time"
    widget show "09:30" and the "hour" widget show "09", in sync.
  * "letter" widgets (week, month, apm) look up a single named image
    directly, e.g. "en_wed.png" - also chosen from PreviewData (the actual
    weekday/month/am-or-pm implied by the current preview date and time).
  * "icon" / "anima" / "redpoint" widgets show a single static image.
"""
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPainter

from . import widget_registry as reg
from .preview_data import PreviewData


def _glyph_key_for_char(ch: str) -> str:
    """Map a preview-value character to the glyph filename stem to look up."""
    if ch.isdigit():
        return ch
    if ch in reg.WEATHER_UNIT_GLYPH:
        return reg.WEATHER_UNIT_GLYPH[ch]
    if ch in reg.SPECIAL_CHAR_GLYPH:
        return reg.SPECIAL_CHAR_GLYPH[ch]
    return ""


def _preview_value_for(type_value: str, json_obj: dict, preview: PreviewData) -> str:
    """
    Compute the on-canvas preview string for a digit widget from the shared,
    user-editable PreviewData - e.g. with preview.hour=9, preview.minute=30:
        "time"    -> "09:30"
        "hour"    -> "09"
        "hourhi"  -> "0"
        "hourlo"  -> "9"
        "min"     -> "30"
        "minhi"   -> "3"
        "minlo"   -> "0"
    This replaces the old single hard-coded demo value per widget type -
    every digit widget now stays in sync with one shared clock/calendar/
    metrics state.
    """
    hh = f"{preview.hour12():02d}"
    mm = f"{preview.minute:02d}"
    ss = f"{preview.second:02d}"
    year, month, day = preview.safe_date_parts()

    if type_value == "time":
        return f"{hh}:{mm}"
    if type_value == "hour":
        return hh
    if type_value == "hourhi":
        return hh[0]
    if type_value == "hourlo":
        return hh[1]
    if type_value == "min":
        return mm
    if type_value == "minhi":
        return mm[0]
    if type_value == "minlo":
        return mm[1]
    if type_value == "second":
        return ss
    if type_value == "date":
        return f"{day:02d}/{month:02d}"
    if type_value == "day":
        return f"{day:02d}"
    if type_value == "year":
        return str(year)
    if type_value == "step":
        return str(int(preview.step))
    if type_value == "calorie":
        return str(int(preview.calorie))
    if type_value == "heartrate":
        return str(int(preview.heartrate))
    if type_value == "distance":
        return f"{preview.distance:.2f}"
    if type_value == "exercise":
        return str(int(preview.exercise))
    if type_value == "walk":
        return str(int(preview.walk))
    if type_value == "battery":
        fontnum = int(json_obj.get("fontnum", 11) or 0)
        value = str(int(preview.battery))
        return value if fontnum <= 10 else value + "%"
    if type_value == "weather":
        style = int(json_obj.get("style", 2) or 2)
        suffix = reg.WEATHER_UNIT_SENTINEL_C if style == 2 else reg.WEATHER_UNIT_SENTINEL_F
        return str(int(preview.weather)) + suffix
    return "0"


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


def render_digit_widget(strip: dict, type_value: str, json_obj: dict, preview: PreviewData) -> QImage:
    value = _preview_value_for(type_value, json_obj, preview)
    glyphs = _collect_glyphs(strip, value)
    if not glyphs:
        return QImage()

    align = json_obj.get("align", "left")
    canvas_w = int(json_obj.get("w", 0) or 0)

    if align == "autowrap":
        return _compose_autowrap(glyphs, canvas_w)
    return _compose_row(glyphs, canvas_w, align)


# Static fallback used only if no PreviewData is available (should not
# normally happen - every call site threads a real PreviewData through).
_LETTER_FALLBACK = {"week": "en_wed", "month": "en_sept", "apm": "en_am"}


def render_letter_widget(strip: dict, type_value: str, preview: PreviewData) -> QImage:
    if type_value == "week":
        key = preview.weekday_glyph_name()
    elif type_value == "month":
        key = preview.month_glyph_name()
    elif type_value == "apm":
        key = preview.apm_glyph_name()
    else:
        key = _LETTER_FALLBACK.get(type_value, "")
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


def render_custom_widget_image(type_value: str, strip: dict, json_obj: dict, preview: PreviewData = None) -> QImage:
    """Dispatch to the correct pure-image renderer for a custom/* widget."""
    if preview is None:
        preview = PreviewData()
    if type_value == "anima":
        return render_static_single_image(strip, "0")
    if type_value == "icon":
        return render_static_single_image(strip, "__icon__")
    if type_value == "redpoint":
        return render_static_single_image(strip, "0")
    if type_value in reg.LETTER_TYPES:
        return render_letter_widget(strip, type_value, preview)
    return render_digit_widget(strip, type_value, json_obj, preview)


def measure_custom_widget(type_value: str, strip: dict, json_obj: dict, preview: PreviewData = None) -> QSize:
    if preview is None:
        preview = PreviewData()
    img = render_custom_widget_image(type_value, strip, json_obj, preview)
    if img.isNull():
        return QSize(50, 20)
    return img.size()
