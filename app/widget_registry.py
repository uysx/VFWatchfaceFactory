"""
Registry-driven widget metadata.

This module holds no rendering or Qt code. It is pure data describing:
  * which "widget" kinds exist ("custom", "watch", "ring", "progressbar")
  * which "type" values are valid for each kind
  * the JSON key order to use when exporting each widget flavor (so exported
    iwf.json matches the reference format's field ordering)
  * preview values used for auto-sizing / on-canvas preview rendering
  * which custom types are image-glyph ("digit") widgets vs named-image
    ("letter") widgets vs special single-image widgets (icon/anima/redpoint)
  * which types are not yet implemented ("coming soon")
"""

# ---------------------------------------------------------------------------
# Widget kind -> allowed type values (mirrors populateTypeCombo in the
# reference editor)
# ---------------------------------------------------------------------------
WIDGET_KIND_TYPES = {
    "custom": [
        "date", "time", "hour", "hourhi", "hourlo", "min", "minhi", "minlo",
        "second", "week", "day", "month", "year",
        "calorie", "distance", "heartrate", "redpoint", "battery",
        "step", "walk", "exercise", "icon", "sleep", "bluetooth", "apm",
        "weather", "shortcut", "anima", "multimeter", "gradient",
    ],
    "watch": ["time"],
}

# Custom types that are not implemented yet - "Add Widget" refuses these.
COMING_SOON = {"multimeter", "gradient", "shortcut", "sleep", "bluetooth"}

# Custom types fully supported when opening an existing iwf.json (rendered
# from image assets).
SUPPORTED_CUSTOM_ON_OPEN = {
    "date", "time", "hour", "hourhi", "hourlo", "min", "minhi", "minlo",
    "second", "week", "day", "month", "year",
    "calorie", "distance", "heartrate", "battery",
    "step", "walk", "exercise", "apm", "weather",
    "anima", "icon", "redpoint",
}

# "Letter" widgets: a single named image is looked up directly (no digit
# composition) - e.g. week -> "en_wed.png"
LETTER_TYPES = {"week", "month", "apm"}

LETTER_BANKS = {
    "week": ["en_sun", "en_mon", "en_tue", "en_wed", "en_thur", "en_fri", "en_sat"],
    "month": ["en_jan", "en_feb", "en_mar", "en_apr", "en_may", "en_june",
              "en_july", "en_aug", "en_sept", "en_oct", "en_nov", "en_dec"],
    "apm": ["en_am", "en_pm"],
}

LETTER_PREVIEW = {"week": "en_wed", "month": "en_sept", "apm": "en_am"}

# NOTE: fixed digit/letter "preview values" used to live here as static
# dicts (DIGIT_PREVIEW / a second copy of LETTER_PREVIEW use). They have
# been superseded by app.preview_data.PreviewData, which computes each
# widget's preview string dynamically from a single shared, user-editable
# clock/calendar/metrics state instead of one hard-coded demo value per
# type. See glyph_render.py's _preview_value_for() and PreviewData's
# weekday_glyph_name()/month_glyph_name()/apm_glyph_name(). LETTER_PREVIEW
# above is kept only as a static fallback for callers that don't have a
# PreviewData instance on hand.

# Non-digit characters that map onto a glyph filename (glyph "10" is the
# conventional slot for punctuation on these fonts, matching the reference).
SPECIAL_CHAR_GLYPH = {
    ":": "10",
    "/": "10",
    "%": "10",
    ".": "10",
    "-": "10",
    "\u00b0": "10",  # bare degree sign
}

# Weather widget appends a unit suffix sentinel resolved to glyph "11"/"12".
WEATHER_UNIT_SENTINEL_C = "\ue001"
WEATHER_UNIT_SENTINEL_F = "\ue002"
WEATHER_UNIT_GLYPH = {
    WEATHER_UNIT_SENTINEL_C: "11",
    WEATHER_UNIT_SENTINEL_F: "12",
}

# ---------------------------------------------------------------------------
# Export key ordering per widget flavor (mirrors prettyJson()'s static
# key-order lists). Any key present in a widget's JSON but not listed here is
# appended afterwards, in insertion order - so nothing is ever silently lost.
# ---------------------------------------------------------------------------
TOP_LEVEL_KEYS = [
    "version", "clouddialversion", "preview", "name", "author",
    "description", "deviceId", "bluetooth", "disturb", "battery",
    "compress", "item", "bkground",
]

WATCH_KEYS = [
    "widget", "type", "x", "y", "w", "h", "fgcolor",
    "hour", "hourcenterx", "hourcentery", "houranchorx", "houranchory",
    "minute", "mincenterx", "mincentery", "minanchorx", "minanchory",
    "second", "seccenterx", "seccentery", "secanchorx", "secanchory",
]

CUSTOM_KEYS = [
    "widget", "type", "x", "y", "w", "h",
    "fgcolor", "fgrender", "align", "metricinch", "style",
    "font", "fontnum",
]

ANIMA_KEYS = [
    "widget", "type", "x", "y", "w", "h",
    "time", "turn", "animatype", "animaicon", "frame", "animabpp", "animaformat",
]

ICON_KEYS = [
    "widget", "type", "x", "y", "w", "h",
    "bgcolor", "bgrender", "bg",
]

REDPOINT_KEYS = [
    "widget", "type", "x", "y", "w", "h",
    "font", "fontnum",
]

GENERIC_KEYS = ["widget", "type", "x", "y", "w", "h"]


def key_order_for(widget_kind: str, type_value: str):
    """Return the canonical key order list for a given widget/type pair."""
    if widget_kind == "watch":
        return WATCH_KEYS
    if widget_kind == "custom":
        if type_value == "anima":
            return ANIMA_KEYS
        if type_value == "icon":
            return ICON_KEYS
        if type_value == "redpoint":
            return REDPOINT_KEYS
        return CUSTOM_KEYS
    return GENERIC_KEYS


# ---------------------------------------------------------------------------
# Default field templates used when creating a brand-new widget entry.
# ---------------------------------------------------------------------------
def default_custom_json(type_value: str, folder_name: str, image_count: int):
    obj = {
        "widget": "custom",
        "type": type_value,
        "x": 0,
        "y": 0,
        "fgcolor": "0xFFFFFFFF",
        "fgrender": "0xFFFFFFFF",
        "align": "left",
    }
    if type_value == "distance":
        obj["metricinch"] = 1
    if type_value == "weather":
        obj["style"] = 2
    if type_value in ("date", "week", "month"):
        obj["style"] = 0
    obj["font"] = folder_name
    obj["fontnum"] = image_count
    return obj
