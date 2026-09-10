"""
Project model.

Holds the in-memory state of one VFWatchfaceFactory project: the ordered
list of widget entries (each backed by a plain dict that mirrors the exact
iwf.json item schema), the font.json item list, the project directory on
disk, and the shared, editable PreviewData that drives what value every
widget's on-canvas preview image is composed from. This module contains no
Qt widgets - only QImage for the in-memory image strips - so it stays
cleanly separable from the UI layer.
"""
import dataclasses
import json
import os
import pathlib
from dataclasses import dataclass, field

from PyQt6.QtGui import QImage

from . import widget_registry as reg
from .device_config import DEFAULT_DEVICE_ID, get_device
from .preview_data import PreviewData


IMAGE_EXTENSIONS = (".png", ".bmp", ".PNG", ".BMP")

# PreviewData is editor-only state (never part of the iwf.json spec) and
# must NOT be written anywhere inside the project folder - that folder's
# contents are exactly what iwf_packer/pack_iwf.py scans and packs, and
# only files the user explicitly added as watch-face assets belong there.
# Instead, preview values are cached per-project in a single file under a
# per-user application-data directory, keyed by the project's absolute
# path, so they still persist across sessions without touching the project
# folder at all.
APP_DATA_DIR = pathlib.Path.home() / ".vfwatchfacefactory"
PREVIEW_CACHE_FILE = APP_DATA_DIR / "preview_cache.json"


def _load_preview_cache() -> dict:
    if not PREVIEW_CACHE_FILE.is_file():
        return {}
    try:
        with open(PREVIEW_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_preview_cache(cache: dict):
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PREVIEW_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f)


def load_image_strip(folder: str) -> dict:
    """Load every PNG/BMP in `folder`, keyed by filename stem (e.g. '0', '10')."""
    strip = {}
    if not folder or not os.path.isdir(folder):
        return strip
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith((".png", ".bmp")):
            continue
        path = os.path.join(folder, name)
        img = QImage(path)
        if img.isNull():
            continue
        stem, _ = os.path.splitext(name)
        strip[stem] = img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    return strip


@dataclass
class WidgetEntry:
    widget_kind: str            # "custom" | "watch" | "ring" | "progressbar"
    type_value: str
    data: dict = field(default_factory=dict)   # the raw JSON item fields
    font_folder: str = ""       # relative folder/file name (images live here)
    image_strip: dict = field(default_factory=dict)   # name -> QImage (in-memory only)

    def label(self) -> str:
        return f"{self.widget_kind} / {self.type_value}"


class Project:
    def __init__(self):
        self.project_dir = ""
        self.project_open = False
        self.device_id = DEFAULT_DEVICE_ID
        self.name = ""
        self.author = "user"
        self.bkground = ""
        self.preview_name = "preview.png"
        self.widgets: list[WidgetEntry] = []
        self.font_items: list[dict] = []   # [{"name":..., "bpp":16, "format":"png"}]
        self._file_counter = 0
        self.preview = PreviewData()

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------
    def new_project(self, base_dir: str, name: str) -> str:
        project_dir = os.path.join(base_dir, name)
        os.makedirs(project_dir, exist_ok=True)

        self.project_dir = project_dir
        self.project_open = True
        self.device_id = DEFAULT_DEVICE_ID
        self.name = name
        self.author = "user"
        self.bkground = ""
        self.preview_name = "preview.png"
        self.widgets = []
        self.font_items = []
        self._file_counter = 0
        self.preview = PreviewData()
        self.load_preview_json()
        return project_dir

    def next_bkground_filename(self, suffix: str) -> str:
        name = f"files{self._file_counter}.{suffix}"
        self._file_counter += 1
        return name

    # ------------------------------------------------------------------
    # PreviewData persistence - a per-user app-data cache keyed by this
    # project's absolute path, NOT a file inside the project folder.
    # ------------------------------------------------------------------
    def save_preview_json(self):
        if not self.project_dir:
            return None
        cache = _load_preview_cache()
        cache[os.path.abspath(self.project_dir)] = dataclasses.asdict(self.preview)
        _save_preview_cache(cache)
        return str(PREVIEW_CACHE_FILE)

    def load_preview_json(self):
        if not self.project_dir:
            return
        cache = _load_preview_cache()
        raw = cache.get(os.path.abspath(self.project_dir))
        if not raw:
            return
        for key, value in raw.items():
            if hasattr(self.preview, key):
                setattr(self.preview, key, value)

    # ------------------------------------------------------------------
    # font.json bookkeeping
    # ------------------------------------------------------------------
    def ensure_font_entry(self, folder_name: str, fmt: str = "png", bpp: int = 16):
        if not folder_name:
            return
        for item in self.font_items:
            if item.get("name") == folder_name:
                return
        self.font_items.append({"name": folder_name, "bpp": bpp, "format": fmt})

    # ------------------------------------------------------------------
    # Widget management
    # ------------------------------------------------------------------
    def add_widget(self, entry: WidgetEntry) -> int:
        self.widgets.append(entry)
        return len(self.widgets) - 1

    def remove_widget(self, index: int):
        if 0 <= index < len(self.widgets):
            del self.widgets[index]

    def find_last_watch(self):
        for entry in reversed(self.widgets):
            if entry.widget_kind == "watch":
                return entry
        return None

    # ------------------------------------------------------------------
    # JSON export (mirrors buildRootJson / prettyJson in the reference editor)
    # ------------------------------------------------------------------
    def build_root_dict(self) -> dict:
        device = get_device(self.device_id)
        root = {
            "version": 1,
            "clouddialversion": 3,
            "preview": self.preview_name,
            "name": self.name,
            "author": self.author,
            "description": device.device_id,
            "deviceId": device.device_id,
            "bluetooth": False,
            "disturb": False,
            "battery": False,
            "compress": "LZ4",
            "item": [entry.data for entry in self.widgets],
            "bkground": self.bkground,
        }
        return root

    def to_pretty_iwf_json(self) -> str:
        """Render iwf.json with a stable, spec-matching key order."""
        root = self.build_root_dict()
        lines = ["{"]
        top_keys = [k for k in reg.TOP_LEVEL_KEYS if k in root]
        for i, key in enumerate(top_keys):
            is_last = i == len(top_keys) - 1
            comma = "" if is_last else ","
            if key == "item":
                items = root["item"]
                if not items:
                    lines.append(f'    "item": []{comma}')
                else:
                    lines.append('    "item": [')
                    for j, item in enumerate(items):
                        item_comma = "" if j == len(items) - 1 else ","
                        lines.append(self._render_item(item, indent=8) + item_comma)
                    lines.append(f"    ]{comma}")
            else:
                lines.append(f'    "{key}": {self._render_value(root[key])}{comma}')
        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def _render_value(value) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        if isinstance(value, (int, float)):
            return str(int(value)) if isinstance(value, int) else json.dumps(value)
        return "null"

    def _render_item(self, item: dict, indent: int) -> str:
        pad = " " * indent
        widget_kind = item.get("widget", "")
        type_value = item.get("type", "")
        order = list(reg.key_order_for(widget_kind, type_value))
        for k in item.keys():
            if k not in order:
                order.append(k)

        parts = []
        for k in order:
            if k not in item:
                continue
            parts.append(f'{pad}    "{k}": {self._render_value(item[k])}')
        inner = ",\n".join(parts)
        return f"{pad}{{\n{inner}\n{pad}}}"

    def to_compact_font_json(self) -> str:
        parts = []
        for item in self.font_items:
            parts.append(
                '{"name":"%s","bpp":%d,"format":"%s"}'
                % (item.get("name", ""), int(item.get("bpp", 16)), item.get("format", "png"))
            )
        return '{"item":[' + ",".join(parts) + "]}"

    # ------------------------------------------------------------------
    # Saving to disk
    # ------------------------------------------------------------------
    def save_iwf_json(self):
        path = os.path.join(self.project_dir, "iwf.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_pretty_iwf_json())
        return path

    def save_font_json(self):
        path = os.path.join(self.project_dir, "font.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_compact_font_json())
        return path

    # ------------------------------------------------------------------
    # Opening an existing iwf.json
    # ------------------------------------------------------------------
    def open_iwf_json(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            root = json.load(f)

        self.project_dir = os.path.dirname(os.path.abspath(path))
        self.project_open = True
        self._file_counter = 0

        self.device_id = root.get("deviceId", DEFAULT_DEVICE_ID) or DEFAULT_DEVICE_ID
        self.name = root.get("name", "")
        self.author = root.get("author", "user")
        self.bkground = root.get("bkground", "")
        self.preview_name = root.get("preview", "preview.png")
        self.widgets = []
        self.font_items = []
        self.preview = PreviewData()
        self.load_preview_json()

        skipped = 0
        for item in root.get("item", []):
            widget_kind = item.get("widget", "")
            type_value = item.get("type", "")

            if widget_kind == "watch" and type_value == "time":
                self.add_widget(WidgetEntry(widget_kind="watch", type_value="time", data=item))
                continue

            if widget_kind == "custom" and type_value == "anima":
                folder = item.get("animaicon", "")
                strip = load_image_strip(os.path.join(self.project_dir, folder))
                self.add_widget(WidgetEntry(
                    widget_kind="custom", type_value="anima", data=item,
                    font_folder=folder, image_strip=strip,
                ))
                fmt = (item.get("animaformat") or "png").lower()
                self.ensure_font_entry(folder, fmt)
                continue

            if widget_kind == "custom" and type_value == "icon":
                bg_file = item.get("bg", "")
                path_img = os.path.join(self.project_dir, bg_file)
                strip = {}
                if os.path.isfile(path_img):
                    img = QImage(path_img)
                    if not img.isNull():
                        strip["__icon__"] = img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
                self.add_widget(WidgetEntry(
                    widget_kind="custom", type_value="icon", data=item,
                    font_folder=bg_file, image_strip=strip,
                ))
                continue

            if widget_kind == "custom" and type_value in reg.SUPPORTED_CUSTOM_ON_OPEN:
                folder = item.get("font", "")
                strip = load_image_strip(os.path.join(self.project_dir, folder))
                if "align" not in item:
                    item["align"] = "left"
                self.add_widget(WidgetEntry(
                    widget_kind="custom", type_value=type_value, data=item,
                    font_folder=folder, image_strip=strip,
                ))
                self.ensure_font_entry(folder, "png")
                continue

            skipped += 1

        return skipped
