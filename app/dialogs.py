"""Modal dialogs used by the main window."""
import os
import shutil

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QFileDialog,
    QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
)
from PyQt6.QtGui import QPixmap, QImage


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. my_first_dial")
        layout.addRow("Project name:", self.name_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def project_name(self) -> str:
        return self.name_edit.text().strip()


class ClockHandDialog(QDialog):
    """Pick a hand image plus its pivot ('center') point in the source image
    and the anchor point on the watch face where that pivot should sit."""

    def __init__(self, hand_label: str, default_anchor_x: int, default_anchor_y: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{hand_label.capitalize()} Hand")
        self._file_path = ""

        outer = QVBoxLayout(self)

        pick_row = QHBoxLayout()
        self.path_label = QLabel("(no file selected)")
        self.path_label.setWordWrap(True)
        pick_btn = QPushButton("Choose Image…")
        pick_btn.clicked.connect(self._choose_file)
        pick_row.addWidget(self.path_label, 1)
        pick_row.addWidget(pick_btn)
        outer.addLayout(pick_row)

        self.preview = QLabel()
        self.preview.setFixedHeight(80)
        outer.addWidget(self.preview)

        form = QFormLayout()
        self.center_x = QSpinBox(); self.center_x.setRange(-2000, 2000)
        self.center_y = QSpinBox(); self.center_y.setRange(-2000, 2000)
        self.anchor_x = QSpinBox(); self.anchor_x.setRange(-2000, 2000)
        self.anchor_y = QSpinBox(); self.anchor_y.setRange(-2000, 2000)
        self.anchor_x.setValue(default_anchor_x)
        self.anchor_y.setValue(default_anchor_y)
        form.addRow("Pivot X (in image):", self.center_x)
        form.addRow("Pivot Y (in image):", self.center_y)
        form.addRow("Anchor X (on face):", self.anchor_x)
        form.addRow("Anchor Y (on face):", self.anchor_y)
        outer.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select hand image", "", "Images (*.png *.bmp)")
        if not path:
            return
        self._file_path = path
        self.path_label.setText(path)
        img = QImage(path)
        if not img.isNull():
            self.preview.setPixmap(QPixmap.fromImage(img).scaledToHeight(76))
            # Sensible default pivot: image center (user can override).
            self.center_x.setValue(img.width() // 2)
            self.center_y.setValue(img.height() // 2)

    def file_path(self) -> str:
        return self._file_path

    def file_name(self) -> str:
        return os.path.basename(self._file_path) if self._file_path else ""

    def center_point(self):
        return self.center_x.value(), self.center_y.value()

    def anchor_point(self):
        return self.anchor_x.value(), self.anchor_y.value()


class FolderNameDialog(QDialog):
    """Ask for the font/asset folder name (used for custom digit/letter widgets)."""

    def __init__(self, type_value: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Font Folder Name")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(type_value)
        layout.addRow(
            QLabel("Folder name for this widget's glyph images\n"
                   "(created inside the project directory):")
        )
        layout.addRow("Folder name:", self.name_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def folder_name(self) -> str:
        return self.name_edit.text().strip()


def copy_images_to_folder(file_paths, dest_folder: str):
    """Copy each selected file into dest_folder, returning (count, ext)."""
    os.makedirs(dest_folder, exist_ok=True)
    count = 0
    ext = ""
    for src in file_paths:
        suffix = os.path.splitext(src)[1].lstrip(".").lower()
        if not ext:
            ext = suffix
        dst = os.path.join(dest_folder, os.path.basename(src))
        if os.path.exists(dst):
            os.remove(dst)
        shutil.copy2(src, dst)
        count += 1
    return count, (ext or "png")
