"""Main application window for VFWatchfaceFactory."""
import os

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QImage, QPainter, QPainterPath, QPen, QColor, QAction
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QGroupBox, QFormLayout,
    QComboBox, QPushButton, QGraphicsView, QSplitter, QTabWidget, QPlainTextEdit,
    QFileDialog, QMessageBox
)

from . import widget_registry as reg
from . import glyph_render
from .device_config import get_device
from .project import Project, WidgetEntry, load_image_strip
from .canvas_scene import CanvasScene
from .properties_panel import PropertiesPanel
from .preview_panel import PreviewValuesPanel
from .dialogs import NewProjectDialog, ClockHandDialog, FolderNameDialog, copy_images_to_folder


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VFWatchfaceFactory")
        self.resize(1400, 900)

        self.project = Project()
        self.current_index = -1

        self._build_ui()
        self._build_menu()
        self._set_project_controls_enabled(False)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        splitter.addWidget(self._build_left_panel())

        self.scene = CanvasScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setBackgroundBrush(QColor("#0c0c0f"))
        splitter.addWidget(self.view)

        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([320, 700, 380])

        self.statusBar().showMessage("Ready. Start a New Project to begin.")

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(300)
        panel.setMaximumWidth(380)
        layout = QVBoxLayout(panel)

        # --- Preview values (clock/calendar/metrics every widget previews against) ---
        self.preview_panel = PreviewValuesPanel()
        self.preview_panel.changed.connect(self._on_preview_values_changed)
        layout.addWidget(self.preview_panel)

        # --- Add widget ---
        add_box = QGroupBox("Add Widget")
        form = QFormLayout(add_box)
        self.kind_combo = QComboBox()
        self.kind_combo.addItems(list(reg.WIDGET_KIND_TYPES.keys()))
        self.kind_combo.currentTextChanged.connect(self._populate_type_combo)
        self.type_combo = QComboBox()
        form.addRow("Widget", self.kind_combo)
        form.addRow("Type", self.type_combo)
        self.add_widget_btn = QPushButton("Add Widget")
        self.add_widget_btn.setObjectName("primaryButton")
        self.add_widget_btn.clicked.connect(self._on_add_widget)
        form.addRow(self.add_widget_btn)
        layout.addWidget(add_box)
        self._populate_type_combo(self.kind_combo.currentText())

        # --- Current widget ---
        cur_box = QGroupBox("Selected Widget")
        cur_layout = QVBoxLayout(cur_box)
        self.current_combo = QComboBox()
        self.current_combo.currentIndexChanged.connect(self._on_select_widget)
        cur_layout.addWidget(self.current_combo)
        self.remove_btn = QPushButton("Remove Widget")
        self.remove_btn.clicked.connect(self._on_remove_widget)
        cur_layout.addWidget(self.remove_btn)
        layout.addWidget(cur_box)

        # --- Properties ---
        self.properties = PropertiesPanel()
        self.properties.geometry_changed.connect(self._on_geometry_changed)
        self.properties.fields_changed.connect(self._on_fields_changed)
        layout.addWidget(self.properties, 1)

        # --- Background / preview ---
        misc_box = QGroupBox("Canvas")
        misc_layout = QVBoxLayout(misc_box)
        bg_btn = QPushButton("Upload Background…")
        bg_btn.clicked.connect(self._on_upload_background)
        preview_btn = QPushButton("Save Preview PNG")
        preview_btn.clicked.connect(self._on_save_preview)
        misc_layout.addWidget(bg_btn)
        misc_layout.addWidget(preview_btn)
        layout.addWidget(misc_box)

        self._left_controls = [
            self.kind_combo, self.type_combo, self.add_widget_btn,
            self.current_combo, self.remove_btn, self.properties,
            self.preview_panel,
        ]
        self._canvas_controls = [bg_btn, preview_btn]
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(340)
        panel.setMaximumWidth(460)
        layout = QVBoxLayout(panel)

        tabs = QTabWidget()

        iwf_tab = QWidget()
        iwf_layout = QVBoxLayout(iwf_tab)
        self.iwf_text = QPlainTextEdit()
        self.iwf_text.setReadOnly(True)
        self.iwf_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        iwf_layout.addWidget(self.iwf_text)
        self.save_iwf_btn = QPushButton("Save iwf.json")
        self.save_iwf_btn.clicked.connect(self._on_save_iwf_json)
        iwf_layout.addWidget(self.save_iwf_btn)
        tabs.addTab(iwf_tab, "iwf.json")

        font_tab = QWidget()
        font_layout = QVBoxLayout(font_tab)
        self.font_text = QPlainTextEdit()
        self.font_text.setReadOnly(True)
        self.font_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        font_layout.addWidget(self.font_text)
        self.save_font_btn = QPushButton("Save font.json")
        self.save_font_btn.clicked.connect(self._on_save_font_json)
        font_layout.addWidget(self.save_font_btn)
        tabs.addTab(font_tab, "font.json")

        layout.addWidget(tabs)
        self._json_controls = [self.save_iwf_btn, self.save_font_btn]
        return panel

    def _build_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        new_action = QAction("&New Project…", self)
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open iwf.json…", self)
        open_action.triggered.connect(self._on_open_iwf_json)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_iwf_action = QAction("Save iwf.json", self)
        save_iwf_action.triggered.connect(self._on_save_iwf_json)
        file_menu.addAction(save_iwf_action)

        save_font_action = QAction("Save font.json", self)
        save_font_action.triggered.connect(self._on_save_font_json)
        file_menu.addAction(save_font_action)

        save_preview_action = QAction("Save Preview PNG", self)
        save_preview_action.triggered.connect(self._on_save_preview)
        file_menu.addAction(save_preview_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------
    def _set_project_controls_enabled(self, enabled: bool):
        for w in self._left_controls + self._canvas_controls + self._json_controls:
            w.setEnabled(enabled)

    def _populate_type_combo(self, kind: str):
        self.type_combo.clear()
        self.type_combo.addItems(reg.WIDGET_KIND_TYPES.get(kind, []))

    def _refresh_json_views(self):
        self.iwf_text.setPlainText(self.project.to_pretty_iwf_json())
        self.font_text.setPlainText(self.project.to_compact_font_json())

    def _rebuild_widget_combo(self, select_index: int = -1):
        self.current_combo.blockSignals(True)
        self.current_combo.clear()
        for entry in self.project.widgets:
            self.current_combo.addItem(entry.label())
        self.current_combo.blockSignals(False)
        if select_index >= 0:
            self.current_combo.setCurrentIndex(select_index)
            self._select_widget(select_index)
        elif self.project.widgets:
            self.current_combo.setCurrentIndex(0)
        else:
            self._select_widget(-1)

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------
    def _on_new_project(self):
        dlg = NewProjectDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        name = dlg.project_name()
        if not name:
            QMessageBox.warning(self, "Error", "Project name cannot be empty.")
            return
        base_dir = QFileDialog.getExistingDirectory(self, "Select directory to place the project")
        if not base_dir:
            return

        project_dir = self.project.new_project(base_dir, name)
        device = get_device(self.project.device_id)
        self.scene.reset(device.canvas_w, device.canvas_h)
        self.current_index = -1
        self.preview_panel.load(self.project.preview)
        self._rebuild_widget_combo()
        self._refresh_json_views()
        self._set_project_controls_enabled(True)
        QMessageBox.information(self, "Project Created", f'Project "{name}" created at:\n{project_dir}')

    def _on_open_iwf_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open iwf.json", "", "JSON files (*.json)")
        if not path:
            return
        try:
            skipped = self.project.open_iwf_json(path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not open iwf.json:\n{exc}")
            return

        self.scene.render_all(self.project)
        self.preview_panel.load(self.project.preview)
        self._rebuild_widget_combo(0 if self.project.widgets else -1)
        self._refresh_json_views()
        self._set_project_controls_enabled(True)

        msg = f"Loaded {len(self.project.widgets)} widget(s) from {os.path.basename(path)}"
        if skipped:
            msg += f" ({skipped} unsupported widget(s) skipped)"
        self.statusBar().showMessage(msg)

    def _on_save_iwf_json(self):
        if not self.project.project_open:
            QMessageBox.warning(self, "No Project", "Please create or open a project first.")
            return
        path = self.project.save_iwf_json()
        self.statusBar().showMessage(f"Saved {path}")

    def _on_save_font_json(self):
        if not self.project.project_open:
            QMessageBox.warning(self, "No Project", "Please create or open a project first.")
            return
        path = self.project.save_font_json()
        self.statusBar().showMessage(f"Saved {path}")

    def _on_about(self):
        QMessageBox.information(
            self, "About VFWatchfaceFactory",
            "VFWatchfaceFactory\n\n"
            "A watch face editor for VeryFit smartwatches (IDW13).\n"
            "Successor / inspired replacement for ArnCep's ATSDialFactory."
        )

    # ------------------------------------------------------------------
    # Background / preview
    # ------------------------------------------------------------------
    def _on_upload_background(self):
        if not self.project.project_open:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Select Background Image", "", "Images (*.png *.bmp)")
        if not path:
            return
        suffix = os.path.splitext(path)[1].lstrip(".").lower()
        if suffix not in ("png", "bmp"):
            QMessageBox.critical(self, "Invalid File Type", "Only PNG and BMP files are supported.")
            return
        dest_name = self.project.next_bkground_filename(suffix)
        dest_path = os.path.join(self.project.project_dir, dest_name)
        img = QImage(path)
        if img.isNull():
            QMessageBox.critical(self, "Error", "Failed to load the image file.")
            return
        img.save(dest_path)

        self.project.bkground = dest_name
        self.scene.set_background(self.project.project_dir, dest_name)
        self._refresh_json_views()

    def _on_save_preview(self):
        if not self.project.project_open:
            QMessageBox.warning(
                self,
                "No Project",
                "Please create or open a project first."
            )
            return
    
        device = get_device(self.project.device_id)
    
        # Render the watch face at native resolution.
        scene_img = self.scene.render_scene_to_image(
            device.canvas_w,
            device.canvas_h,
        )
    
        # --------------------------------------------------------------
        # Fit the watch face INSIDE the preview border.
        # --------------------------------------------------------------
    
        fit_scale = min(
            device.border_rect_w / device.canvas_w,
            device.border_rect_h / device.canvas_h,
        ) * device.preview_scale
    
        scaled_w = max(1, round(device.canvas_w * fit_scale))
        scaled_h = max(1, round(device.canvas_h * fit_scale))
    
        scaled = scene_img.scaled(
            scaled_w,
            scaled_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    
        # --------------------------------------------------------------
        # Create final preview.
        # --------------------------------------------------------------
    
        final = QImage(
            device.preview_w,
            device.preview_h,
            QImage.Format.Format_RGB888,
        )
        final.fill(Qt.GlobalColor.black)
    
        painter = QPainter(final)
    
        try:
            painter.setRenderHint(
                QPainter.RenderHint.Antialiasing,
                True,
            )
            painter.setRenderHint(
                QPainter.RenderHint.SmoothPixmapTransform,
                True,
            )
    
            # ----------------------------------------------------------
            # Calculate border position.
            # ----------------------------------------------------------
    
            border_x = (
                device.preview_w - device.border_rect_w
            ) / 2.0
    
            border_y = (
                device.preview_h - device.border_rect_h
            ) / 2.0
    
            # ----------------------------------------------------------
            # Center scaled watch face inside border.
            # ----------------------------------------------------------
    
            face_x = (
                border_x
                + (device.border_rect_w - scaled.width()) / 2.0
            )
    
            face_y = (
                border_y
                + (device.border_rect_h - scaled.height()) / 2.0
            )
    
            # ----------------------------------------------------------
            # Clip watch face to rounded rectangle.
            # ----------------------------------------------------------
    
            face_radius = device.corner_radius * fit_scale
    
            clip_path = QPainterPath()
            clip_path.addRoundedRect(
                QRectF(
                    face_x,
                    face_y,
                    scaled.width(),
                    scaled.height(),
                ),
                float(face_radius),
                float(face_radius),
            )
    
            painter.save()
            painter.setClipPath(clip_path)
    
            painter.drawImage(
                round(face_x),
                round(face_y),
                scaled,
            )
    
            painter.restore()
    
            # ----------------------------------------------------------
            # Draw preview border.
            # ----------------------------------------------------------
    
            painter.setPen(
                QPen(
                    QColor(*device.border_color),
                    device.border_width,
                )
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
    
            half_pen = device.border_width / 2.0
    
            border_rect = QRectF(
                border_x + half_pen,
                border_y + half_pen,
                device.border_rect_w - device.border_width,
                device.border_rect_h - device.border_width,
            )
    
            painter.drawRoundedRect(
                border_rect,
                float(device.corner_radius),
                float(device.corner_radius),
            )
    
        finally:
            # VERY IMPORTANT:
            # QPainter must be ended before QImage is destroyed.
            painter.end()
    
        # --------------------------------------------------------------
        # Save after painter has completely finished.
        # --------------------------------------------------------------
    
        out_path = os.path.join(
            self.project.project_dir,
            "preview.png",
        )
    
        if not final.save(out_path, "PNG"):
            QMessageBox.critical(
                self,
                "Error",
                f'Could not save preview to "{out_path}"'
            )
            return
    
        self.project.preview_name = "preview.png"
        self._refresh_json_views()
    
        QMessageBox.information(
            self,
            "Saved",
            f'Successfully saved preview to '
            f'"{self.project.project_dir}"'
        )

    # ------------------------------------------------------------------
    # Widget selection / editing
    # ------------------------------------------------------------------
    def _on_select_widget(self, index: int):
        self._select_widget(index)

    def _select_widget(self, index: int):
        self.current_index = index
        if index < 0 or index >= len(self.project.widgets):
            self.properties.clear()
            self.scene.update_selection(self.project, -1)
            return
        entry = self.project.widgets[index]
        self.properties.load_entry(entry.data)
        self.scene.update_selection(self.project, index)

    def _on_geometry_changed(self, x: int, y: int, w: int, h: int):
        if self.current_index < 0:
            return
        entry = self.project.widgets[self.current_index]
        entry.data["x"] = x
        entry.data["y"] = y
        entry.data["w"] = w
        entry.data["h"] = h
        # Re-render so alignment (which depends on w) stays correct, then
        # move the yellow selection box to match.
        self.scene.render_widget(self.project, self.current_index, preserve_size=True)
        self.scene.update_selection(self.project, self.current_index)
        self._rebuild_widget_combo_label_only()
        self._refresh_json_views()

    def _on_fields_changed(self, fields: dict):
        if self.current_index < 0:
            return
        entry = self.project.widgets[self.current_index]
        for k in list(entry.data.keys()):
            if k in ("widget", "type", "x", "y", "w", "h"):
                continue
            del entry.data[k]
        entry.data.update(fields)
        self.scene.render_widget(self.project, self.current_index, preserve_size=True)
        self.scene.update_selection(self.project, self.current_index)
        self._refresh_json_views()

    def _on_preview_values_changed(self):
        self.preview_panel.apply_to(self.project.preview)
        for i in range(len(self.project.widgets)):
            self.scene.render_widget(self.project, i, preserve_size=True)
        if self.current_index >= 0:
            self.scene.update_selection(self.project, self.current_index)
        if self.project.project_open:
            try:
                self.project.save_preview_json()
            except OSError:
                pass

    def _rebuild_widget_combo_label_only(self):
        self.current_combo.blockSignals(True)
        for i, entry in enumerate(self.project.widgets):
            self.current_combo.setItemText(i, entry.label())
        self.current_combo.blockSignals(False)

    def _on_remove_widget(self):
        if self.current_index < 0:
            return
        self.scene.remove_widget_items(self.current_index)
        self.scene.reindex_after_removal(self.current_index)
        self.project.remove_widget(self.current_index)
        self.scene.update_selection(self.project, -1)
        next_index = min(self.current_index, len(self.project.widgets) - 1)
        self._rebuild_widget_combo(next_index)
        self._refresh_json_views()

    # ------------------------------------------------------------------
    # Add widget
    # ------------------------------------------------------------------
    def _on_add_widget(self):
        if not self.project.project_open:
            QMessageBox.warning(self, "No Project", "Please create a project first.")
            return

        kind = self.kind_combo.currentText()
        type_value = self.type_combo.currentText()
        if not type_value:
            return

        if kind == "watch" and type_value == "time":
            self._add_watch_widget()
            return

        if kind == "custom":
            if type_value in reg.COMING_SOON:
                QMessageBox.information(self, "Coming Soon", f'The "{type_value}" type is coming soon.')
                return
            if type_value == "anima":
                self._add_anima_widget()
            elif type_value == "redpoint":
                self._add_redpoint_widget()
            elif type_value == "icon":
                self._add_icon_widget()
            else:
                self._add_custom_digit_widget(type_value)
            return

        # ring / progressbar - generic placeholder, rendering type not yet
        # implemented (matches the reference editor's own scope).
        device = get_device(self.project.device_id)
        data = {
            "widget": kind, "type": type_value,
            "x": 0, "y": 0, "w": device.canvas_w, "h": device.canvas_h,
        }
        entry = WidgetEntry(widget_kind=kind, type_value=type_value, data=data)
        new_idx = self.project.add_widget(entry)
        self.scene.render_widget(self.project, new_idx)
        self._rebuild_widget_combo(new_idx)
        self._refresh_json_views()

    def _add_watch_widget(self):
        device = get_device(self.project.device_id)
        hour_dlg = ClockHandDialog("hour", device.anchor_x, device.anchor_y, self)
        if hour_dlg.exec() != hour_dlg.DialogCode.Accepted or not hour_dlg.file_path():
            return
        min_dlg = ClockHandDialog("minute", device.anchor_x, device.anchor_y, self)
        if min_dlg.exec() != min_dlg.DialogCode.Accepted or not min_dlg.file_path():
            return
        sec_dlg = ClockHandDialog("second", device.anchor_x, device.anchor_y, self)
        if sec_dlg.exec() != sec_dlg.DialogCode.Accepted or not sec_dlg.file_path():
            return

        def copy_hand(dlg: ClockHandDialog) -> str:
            dest_name = os.path.basename(dlg.file_path())
            dest_path = os.path.join(self.project.project_dir, dest_name)
            img = QImage(dlg.file_path())
            img.save(dest_path)
            return dest_name

        hour_file = copy_hand(hour_dlg)
        min_file = copy_hand(min_dlg)
        sec_file = copy_hand(sec_dlg)

        hcx, hcy = hour_dlg.center_point(); hax, hay = hour_dlg.anchor_point()
        mcx, mcy = min_dlg.center_point(); manx, many = min_dlg.anchor_point()
        scx, scy = sec_dlg.center_point(); sax, say = sec_dlg.anchor_point()

        data = {
            "widget": "watch", "type": "time",
            "x": 0, "y": 0, "w": get_device(self.project.device_id).canvas_w,
            "h": get_device(self.project.device_id).canvas_h,
            "fgcolor": "0xFFFFFFFF",
            "hour": hour_file, "hourcenterx": hcx, "hourcentery": hcy,
            "houranchorx": hax, "houranchory": hay,
            "minute": min_file, "mincenterx": mcx, "mincentery": mcy,
            "minanchorx": manx, "minanchory": many,
            "second": sec_file, "seccenterx": scx, "seccentery": scy,
            "secanchorx": sax, "secanchory": say,
        }
        entry = WidgetEntry(widget_kind="watch", type_value="time", data=data)
        idx = self.project.add_widget(entry)
        self.scene.render_widget(self.project, idx)
        self._rebuild_widget_combo(idx)
        self._refresh_json_views()

    def _add_custom_digit_widget(self, type_value: str):
        dlg = FolderNameDialog(type_value, self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        folder_name = dlg.folder_name()
        if not folder_name:
            return

        files, _ = QFileDialog.getOpenFileNames(
            self, f'Select images for "{type_value}" widget (folder: {folder_name})',
            "", "Images (*.png *.bmp)",
        )
        if not files:
            return

        dest_folder = os.path.join(self.project.project_dir, folder_name)
        count, ext = copy_images_to_folder(files, dest_folder)
        strip = load_image_strip(dest_folder)

        data = reg.default_custom_json(type_value, folder_name, count)
        size = glyph_render.measure_custom_widget(type_value, strip, data, self.project.preview)
        data["w"] = size.width() if size.width() > 0 else 50
        data["h"] = size.height() if size.height() > 0 else 20

        self.project.ensure_font_entry(folder_name, ext)

        entry = WidgetEntry(widget_kind="custom", type_value=type_value, data=data,
                             font_folder=folder_name, image_strip=strip)
        idx = self.project.add_widget(entry)
        self.scene.render_widget(self.project, idx)
        self._rebuild_widget_combo(idx)
        self._refresh_json_views()

    def _add_anima_widget(self):
        dlg = FolderNameDialog("anima", self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        folder_name = dlg.folder_name()
        if not folder_name:
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, f"Select animation frames for folder: {folder_name}", "", "Images (*.png *.bmp)",
        )
        if not files:
            return
        dest_folder = os.path.join(self.project.project_dir, folder_name)
        count, ext = copy_images_to_folder(files, dest_folder)
        strip = load_image_strip(dest_folder)

        data = {
            "widget": "custom", "type": "anima",
            "x": 0, "y": 0, "w": 34, "h": 33,
            "time": 1200, "turn": 0, "animatype": "normal",
            "animaicon": folder_name, "frame": count,
            "animabpp": 16, "animaformat": ext,
        }
        if strip:
            first = next(iter(strip.values()))
            data["w"] = first.width()
            data["h"] = first.height()

        self.project.ensure_font_entry(folder_name, ext)
        entry = WidgetEntry(widget_kind="custom", type_value="anima", data=data,
                             font_folder=folder_name, image_strip=strip)
        idx = self.project.add_widget(entry)
        self.scene.render_widget(self.project, idx)
        self._rebuild_widget_combo(idx)
        self._refresh_json_views()

    def _add_redpoint_widget(self):
        dlg = FolderNameDialog("redpoint", self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        folder_name = dlg.folder_name()
        if not folder_name:
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, f"Select images for redpoint widget (folder: {folder_name})", "", "Images (*.png *.bmp)",
        )
        if not files:
            return
        dest_folder = os.path.join(self.project.project_dir, folder_name)
        count, ext = copy_images_to_folder(files, dest_folder)
        strip = load_image_strip(dest_folder)

        first = next(iter(strip.values())) if strip else None
        data = {
            "widget": "custom", "type": "redpoint",
            "x": 0, "y": 0,
            "w": first.width() if first else 20,
            "h": first.height() if first else 20,
            "font": folder_name, "fontnum": count,
        }
        self.project.ensure_font_entry(folder_name, ext)
        entry = WidgetEntry(widget_kind="custom", type_value="redpoint", data=data,
                             font_folder=folder_name, image_strip=strip)
        idx = self.project.add_widget(entry)
        self.scene.render_widget(self.project, idx)
        self._rebuild_widget_combo(idx)
        self._refresh_json_views()

    def _add_icon_widget(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Icon Image", "", "Images (*.png *.bmp)")
        if not path:
            return
        file_name = os.path.basename(path)
        dest_path = os.path.join(self.project.project_dir, file_name)
        img = QImage(path)
        if img.isNull():
            QMessageBox.critical(self, "Error", f"Could not load image:\n{path}")
            return
        img = img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        img.save(dest_path)

        data = {
            "widget": "custom", "type": "icon",
            "x": 0, "y": 0, "w": img.width(), "h": img.height(),
            "bgcolor": "0xFFFFFFFF", "bgrender": "0xFFFFFFFF", "bg": file_name,
        }
        strip = {"__icon__": img}
        entry = WidgetEntry(widget_kind="custom", type_value="icon", data=data,
                             font_folder=file_name, image_strip=strip)
        idx = self.project.add_widget(entry)
        self.scene.render_widget(self.project, idx)
        self._rebuild_widget_combo(idx)
        self._refresh_json_views()
