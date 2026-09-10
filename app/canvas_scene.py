"""
Canvas scene: owns the QGraphicsScene and is responsible for turning Project
widget entries into on-screen QGraphicsPixmapItems.

Nothing in this file uses QPainter.drawText / QFont for widget content. The
only non-image drawing is the yellow selection rectangle, which is explicit
editor-only UI (never serialized into iwf.json).
"""
import os

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem

from . import glyph_render
from . import watch_render
from .project import Project, WidgetEntry
from .device_config import get_device


def _placeholder_image(w: int, h: int) -> QImage:
    """
    Placeholder shown for a widget with no image assets assigned yet (e.g. a
    freshly-added ring/progressbar type still awaiting implementation, or a
    custom widget whose font folder could not be loaded). Deliberately
    contains NO text - only a translucent fill and a dashed border - so the
    "zero text rendering" rule holds even for the empty/error state.
    """
    w = max(w, 1)
    h = max(h, 1)
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(255, 255, 255, 40))
    painter = QPainter(img)
    pen = QPen(QColor(255, 255, 0, 180), 1, Qt.PenStyle.DashLine)
    painter.setPen(pen)
    painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
    painter.drawRect(0, 0, w - 1, h - 1)
    # A small diagonal cross-hatch communicates "no asset" without any text.
    painter.drawLine(0, 0, w - 1, h - 1)
    painter.drawLine(w - 1, 0, 0, h - 1)
    painter.end()
    return img


class CanvasScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bkground_item: QGraphicsPixmapItem | None = None
        self._widget_items: dict[int, list] = {}   # widget index -> list of QGraphicsItems
        self._selection_rect: QGraphicsRectItem | None = None

    # ------------------------------------------------------------------
    def reset(self, canvas_w: int, canvas_h: int):
        self.clear()
        self._bkground_item = None
        self._widget_items = {}
        self._selection_rect = None
        self.setSceneRect(0, 0, canvas_w, canvas_h)

    def set_background(self, project_dir: str, bkground_name: str):
        if self._bkground_item is not None:
            self.removeItem(self._bkground_item)
            self._bkground_item = None
        if not bkground_name:
            return
        path = os.path.join(project_dir, bkground_name)
        if not os.path.isfile(path):
            return
        img = QImage(path)
        if img.isNull():
            return
        item = QGraphicsPixmapItem(QPixmap.fromImage(img))
        item.setZValue(-1000)
        self.addItem(item)
        self._bkground_item = item

    # ------------------------------------------------------------------
    def _clear_widget_items(self, index: int):
        for item in self._widget_items.pop(index, []):
            if item.scene() is self:
                self.removeItem(item)

    def remove_widget_items(self, index: int):
        self._clear_widget_items(index)

    def reindex_after_removal(self, removed_index: int):
        """Shift stored item keys down by one after a widget is deleted."""
        new_map = {}
        for idx, items in self._widget_items.items():
            if idx == removed_index:
                continue
            new_map[idx - 1 if idx > removed_index else idx] = items
        self._widget_items = new_map

    # ------------------------------------------------------------------
    def render_widget(self, project: Project, index: int, preserve_size: bool = False):
        """(Re)render widget `index` and place its scene item(s)."""
        if index < 0 or index >= len(project.widgets):
            return
        entry = project.widgets[index]
        self._clear_widget_items(index)

        if entry.widget_kind == "watch":
            self._render_watch(project, entry, index)
            return

        image = glyph_render.render_custom_widget_image(
            entry.type_value, entry.image_strip, entry.data, project.preview
        ) if entry.widget_kind == "custom" else QImage()

        x = int(entry.data.get("x", 0) or 0)
        y = int(entry.data.get("y", 0) or 0)

        if image.isNull():
            w = int(entry.data.get("w", 50) or 50)
            h = int(entry.data.get("h", 20) or 20)
            display = _placeholder_image(max(w, 1), max(h, 1))
        else:
            display = image
            if not preserve_size:
                entry.data["w"] = image.width()
                entry.data["h"] = image.height()

        item = QGraphicsPixmapItem(QPixmap.fromImage(display))
        item.setPos(x, y)
        self.addItem(item)
        self._widget_items[index] = [item]

    def _render_watch(self, project: Project, entry: WidgetEntry, index: int):
        hands = watch_render.render_watch_hands(project.project_dir, entry.data, project.preview)
        items = []
        for key in ("hour", "minute", "second"):
            hand = hands.get(key)
            if hand is None:
                continue
            item = QGraphicsPixmapItem(QPixmap.fromImage(hand.image))
            item.setPos(hand.pos)
            self.addItem(item)
            items.append(item)
        self._widget_items[index] = items

    def render_all(self, project: Project):
        device = get_device(project.device_id)
        self.reset(device.canvas_w, device.canvas_h)
        self.set_background(project.project_dir, project.bkground)
        for index in range(len(project.widgets)):
            self.render_widget(project, index, preserve_size=True)

    # ------------------------------------------------------------------
    def update_selection(self, project: Project, index: int):
        if self._selection_rect is not None:
            self.removeItem(self._selection_rect)
            self._selection_rect = None
        if index < 0 or index >= len(project.widgets):
            return
        entry = project.widgets[index]
        device = get_device(project.device_id)
        x = int(entry.data.get("x", 0) or 0)
        y = int(entry.data.get("y", 0) or 0)
        w = int(entry.data.get("w", device.canvas_w) or device.canvas_w)
        h = int(entry.data.get("h", device.canvas_h) or device.canvas_h)
        rect = QRectF(x, y, w, h)
        pen = QPen(QColor(255, 220, 0), 1, Qt.PenStyle.SolidLine)
        self._selection_rect = self.addRect(rect, pen, QBrush(Qt.BrushStyle.NoBrush))
        self._selection_rect.setZValue(1000)

    def render_scene_to_image(self, canvas_w: int, canvas_h: int) -> QImage:
        """Render the current scene (widgets + background, no selection box) to a flat image."""
        was_visible = self._selection_rect is not None and self._selection_rect.isVisible()
        if self._selection_rect is not None:
            self._selection_rect.setVisible(False)

        img = QImage(canvas_w, canvas_h, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(0, 0, canvas_w, canvas_h)
        self.render(painter, rect, rect)
        painter.end()

        if self._selection_rect is not None:
            self._selection_rect.setVisible(was_visible)
        return img
