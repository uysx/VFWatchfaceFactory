"""
Property inspector panel.

Mirrors the reference editor's per-widget property sheet: always-visible
X/Y/W/H spin boxes (live, move/resize the selection immediately) plus a
generic, editable key/value table for every other iwf.json field the widget
carries (fgcolor, align, font, fontnum, style, hour/minute/second hand
filenames and their center/anchor points, anima fields, etc). Rows can be
added or removed freely, exactly like the reference editor's per-field
checkbox ("include this key or not") + line-edit table - except expressed as
an ordinary editable table instead of 45 hand-wired checkbox/lineEdit pairs.
"""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QSpinBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QPushButton, QHBoxLayout, QHeaderView,
    QInputDialog,
)

# Keys managed by the dedicated X/Y/W/H spinboxes - never shown in the
# generic field table (would be redundant / confusing to edit in two places).
GEOMETRY_KEYS = {"x", "y", "w", "h"}
# Keys that are structural / not meant for free-text editing here.
STRUCTURAL_KEYS = {"widget", "type"}


class PropertiesPanel(QWidget):
    geometry_changed = pyqtSignal(int, int, int, int)   # x, y, w, h
    fields_changed = pyqtSignal(dict)                    # full replacement dict of extra fields

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self._entry_data = {}

        outer = QVBoxLayout(self)

        geo_box = QGroupBox("Geometry")
        form = QFormLayout(geo_box)
        self.x_spin = QSpinBox(); self.x_spin.setRange(-4000, 4000)
        self.y_spin = QSpinBox(); self.y_spin.setRange(-4000, 4000)
        self.w_spin = QSpinBox(); self.w_spin.setRange(0, 4000)
        self.h_spin = QSpinBox(); self.h_spin.setRange(0, 4000)
        for spin in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
            spin.valueChanged.connect(self._emit_geometry)
        form.addRow("X", self.x_spin)
        form.addRow("Y", self.y_spin)
        form.addRow("W", self.w_spin)
        form.addRow("H", self.h_spin)
        outer.addWidget(geo_box)

        fields_box = QGroupBox("Fields")
        fbox = QVBoxLayout(fields_box)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)
        fbox.addWidget(self.table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Field")
        add_btn.clicked.connect(self._add_field)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        fbox.addLayout(btn_row)

        outer.addWidget(fields_box, 1)

    # ------------------------------------------------------------------
    def load_entry(self, data: dict):
        self._loading = True
        self._entry_data = data
        self.x_spin.setValue(int(data.get("x", 0) or 0))
        self.y_spin.setValue(int(data.get("y", 0) or 0))
        self.w_spin.setValue(int(data.get("w", 0) or 0))
        self.h_spin.setValue(int(data.get("h", 0) or 0))

        self.table.setRowCount(0)
        for key, value in data.items():
            if key in GEOMETRY_KEYS or key in STRUCTURAL_KEYS:
                continue
            self._append_row(key, value)
        self._loading = False

    def clear(self):
        self._loading = True
        self._entry_data = {}
        for spin in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
            spin.setValue(0)
        self.table.setRowCount(0)
        self._loading = False

    # ------------------------------------------------------------------
    def _append_row(self, key, value):
        row = self.table.rowCount()
        self.table.insertRow(row)
        key_item = QTableWidgetItem(str(key))
        val_item = QTableWidgetItem(_value_to_str(value))
        self.table.setItem(row, 0, key_item)
        self.table.setItem(row, 1, val_item)

    def _emit_geometry(self):
        if self._loading:
            return
        self.geometry_changed.emit(
            self.x_spin.value(), self.y_spin.value(),
            self.w_spin.value(), self.h_spin.value(),
        )

    def _on_item_changed(self, _item):
        if self._loading:
            return
        self._emit_fields()

    def _emit_fields(self):
        result = {}
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            val_item = self.table.item(row, 1)
            if key_item is None or not key_item.text().strip():
                continue
            key = key_item.text().strip()
            raw = val_item.text() if val_item is not None else ""
            result[key] = _parse_value(raw)
        self.fields_changed.emit(result)

    def _add_field(self):
        key, ok = QInputDialog.getText(self, "Add Field", "Field name:")
        if not ok or not key.strip():
            return
        self._loading = True
        self._append_row(key.strip(), "")
        self._loading = False
        self._emit_fields()

    def _remove_selected(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        self._loading = True
        for row in rows:
            self.table.removeRow(row)
        self._loading = False
        self._emit_fields()


def _value_to_str(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _parse_value(text: str):
    stripped = text.strip()
    if stripped.lower() == "true":
        return True
    if stripped.lower() == "false":
        return False
    try:
        return int(stripped)
    except ValueError:
        return stripped
