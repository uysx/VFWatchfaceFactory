"""
Preview Values panel.

Lets the user set the "pretend" clock, calendar date, and other live
metrics (battery, heart rate, steps, distance, ...) that every custom
widget's on-canvas preview image is composed from, and that the watch/time
widget's hands rotate to. Nothing here is written into iwf.json - it only
controls what you SEE while editing, replacing the old single hard-coded
demo value every widget used to preview against.

Weekday and AM/PM are shown as read-only derived labels (computed from the
date/hour you set) so it's obvious what glyph each "week"/"apm" widget will
actually display - there is no separate, independently-settable weekday
field to drift out of sync with the date.
"""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QGroupBox, QFormLayout, QGridLayout, QVBoxLayout, QSpinBox,
    QDoubleSpinBox, QComboBox, QLabel,
)

from .preview_data import PreviewData, WEEKDAY_DISPLAY_NAMES

MONTH_LABELS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class PreviewValuesPanel(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        box = QGroupBox("Preview Values")
        layout = QVBoxLayout(box)

        # --- Clock ---
        layout.addWidget(QLabel("Clock"))
        clock_grid = QGridLayout()
        self.hour_spin = QSpinBox(); self.hour_spin.setRange(0, 23)
        self.minute_spin = QSpinBox(); self.minute_spin.setRange(0, 59)
        self.second_spin = QSpinBox(); self.second_spin.setRange(0, 59)
        clock_grid.addWidget(QLabel("H"), 0, 0)
        clock_grid.addWidget(self.hour_spin, 0, 1)
        clock_grid.addWidget(QLabel("M"), 0, 2)
        clock_grid.addWidget(self.minute_spin, 0, 3)
        clock_grid.addWidget(QLabel("S"), 0, 4)
        clock_grid.addWidget(self.second_spin, 0, 5)
        layout.addLayout(clock_grid)

        self.apm_label = QLabel("AM")
        layout.addWidget(self.apm_label)

        # --- Date ---
        layout.addWidget(QLabel("Date"))
        date_grid = QGridLayout()
        self.year_spin = QSpinBox(); self.year_spin.setRange(1970, 2099)
        self.month_combo = QComboBox(); self.month_combo.addItems(MONTH_LABELS)
        self.day_spin = QSpinBox(); self.day_spin.setRange(1, 31)
        date_grid.addWidget(QLabel("Year"), 0, 0)
        date_grid.addWidget(self.year_spin, 0, 1)
        date_grid.addWidget(QLabel("Month"), 1, 0)
        date_grid.addWidget(self.month_combo, 1, 1)
        date_grid.addWidget(QLabel("Day"), 2, 0)
        date_grid.addWidget(self.day_spin, 2, 1)
        layout.addLayout(date_grid)

        self.weekday_label = QLabel("Sunday")
        layout.addWidget(self.weekday_label)

        # --- Metrics ---
        layout.addWidget(QLabel("Metrics"))
        form = QFormLayout()
        self.battery_spin = QSpinBox(); self.battery_spin.setRange(0, 100)
        self.heartrate_spin = QSpinBox(); self.heartrate_spin.setRange(0, 300)
        self.calorie_spin = QSpinBox(); self.calorie_spin.setRange(0, 99999)
        self.distance_spin = QDoubleSpinBox(); self.distance_spin.setRange(0, 999.99)
        self.distance_spin.setDecimals(2)
        self.step_spin = QSpinBox(); self.step_spin.setRange(0, 999999)
        self.walk_spin = QSpinBox(); self.walk_spin.setRange(0, 999)
        self.exercise_spin = QSpinBox(); self.exercise_spin.setRange(0, 999)
        self.weather_spin = QSpinBox(); self.weather_spin.setRange(-60, 60)
        form.addRow("Battery %", self.battery_spin)
        form.addRow("Heart Rate", self.heartrate_spin)
        form.addRow("Calories", self.calorie_spin)
        form.addRow("Distance", self.distance_spin)
        form.addRow("Steps", self.step_spin)
        form.addRow("Walk (min)", self.walk_spin)
        form.addRow("Exercise (min)", self.exercise_spin)
        form.addRow("Weather", self.weather_spin)
        layout.addLayout(form)

        outer.addWidget(box)

        for spin in (
            self.hour_spin, self.minute_spin, self.second_spin,
            self.year_spin, self.day_spin,
            self.battery_spin, self.heartrate_spin, self.calorie_spin,
            self.distance_spin, self.step_spin, self.walk_spin,
            self.exercise_spin, self.weather_spin,
        ):
            spin.valueChanged.connect(self._on_any_changed)
        self.month_combo.currentIndexChanged.connect(self._on_any_changed)

    # ------------------------------------------------------------------
    def load(self, preview: PreviewData):
        """Populate the controls from `preview` without emitting `changed`."""
        self._loading = True
        self.hour_spin.setValue(preview.hour)
        self.minute_spin.setValue(preview.minute)
        self.second_spin.setValue(preview.second)
        self.year_spin.setValue(preview.year)
        self.month_combo.setCurrentIndex(max(0, min(11, preview.month - 1)))
        self.day_spin.setValue(preview.day)
        self.battery_spin.setValue(preview.battery)
        self.heartrate_spin.setValue(preview.heartrate)
        self.calorie_spin.setValue(preview.calorie)
        self.distance_spin.setValue(preview.distance)
        self.step_spin.setValue(preview.step)
        self.walk_spin.setValue(preview.walk)
        self.exercise_spin.setValue(preview.exercise)
        self.weather_spin.setValue(preview.weather)
        self._loading = False
        self._update_derived_labels(preview)

    def apply_to(self, preview: PreviewData):
        """Write the controls' current values back into `preview` in place."""
        preview.hour = self.hour_spin.value()
        preview.minute = self.minute_spin.value()
        preview.second = self.second_spin.value()
        preview.year = self.year_spin.value()
        preview.month = self.month_combo.currentIndex() + 1
        preview.day = self.day_spin.value()
        preview.battery = self.battery_spin.value()
        preview.heartrate = self.heartrate_spin.value()
        preview.calorie = self.calorie_spin.value()
        preview.distance = self.distance_spin.value()
        preview.step = self.step_spin.value()
        preview.walk = self.walk_spin.value()
        preview.exercise = self.exercise_spin.value()
        preview.weather = self.weather_spin.value()
        self._update_derived_labels(preview)

    def _update_derived_labels(self, preview: PreviewData):
        self.apm_label.setText("PM" if preview.is_pm() else "AM")
        self.weekday_label.setText(WEEKDAY_DISPLAY_NAMES[preview.weekday_index()])

    def _on_any_changed(self, *_args):
        if self._loading:
            return
        self.changed.emit()
