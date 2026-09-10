"""
Centralized, editable preview data.

Nothing in this module is ever written into iwf.json - it exists purely to
drive what value each widget's on-canvas image is composed from while you
edit (and what a brand-new widget is auto-sized against). Before this
module existed, every widget always previewed a single hard-coded demo
value ("10:08", "839", "en_wed", ...). Now the whole face previews
consistently against one shared, user-editable clock/calendar/metrics
state - so setting the clock to 9:30 makes the "time" widget show "09:30",
the "hour" widget show "09", the "hourhi"/"hourlo" widgets show "0"/"9", the
"apm" widget switch to "en_am", etc., all at once.

Calendar fields (year/month/day) are the source of truth for the weekday -
weekday is *derived*, never stored independently, so it can never drift out
of sync with the date the user actually set.
"""
import datetime
from dataclasses import dataclass

from . import widget_registry as reg

# Sunday-first weekday names, matching widget_registry.LETTER_BANKS["week"]'s
# glyph ordering (index 0 = Sunday ... index 6 = Saturday).
WEEKDAY_DISPLAY_NAMES = [
    "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
]


@dataclass
class PreviewData:
    # --- Clock (24-hour internal storage; digit widgets render 12-hour) ---
    hour: int = 10        # 0-23
    minute: int = 8       # 0-59
    second: int = 36      # 0-59

    # --- Calendar (weekday is derived from these, see weekday_index()) ---
    year: int = 2025
    month: int = 9        # 1-12
    day: int = 24         # 1-31 (clamped to the actual month length)

    # --- Other metric widgets ---
    battery: int = 100
    heartrate: int = 128
    calorie: int = 839
    distance: float = 16.79
    step: int = 23980
    walk: int = 10
    exercise: int = 20
    weather: int = 28

    # ------------------------------------------------------------------
    # Clock helpers
    # ------------------------------------------------------------------
    def hour12(self) -> int:
        """Hour on a 12-hour face: 0/12/24 -> 12, otherwise hour % 12."""
        h = self.hour % 12
        return 12 if h == 0 else h

    def is_pm(self) -> bool:
        return (self.hour % 24) >= 12

    # ------------------------------------------------------------------
    # Calendar helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _days_in_month(year: int, month: int) -> int:
        if month == 12:
            next_month_first = datetime.date(year + 1, 1, 1)
        else:
            next_month_first = datetime.date(year, month + 1, 1)
        return (next_month_first - datetime.date(year, month, 1)).days

    def safe_date_parts(self):
        """Return (year, month, day) clamped to a real calendar date, so a
        stray day=31 in a 30-day month (or similar) never raises instead of
        just rendering something reasonable."""
        y = max(1, min(9999, int(self.year)))
        m = max(1, min(12, int(self.month)))
        last_day = self._days_in_month(y, m)
        d = max(1, min(last_day, int(self.day)))
        return y, m, d

    def weekday_index(self) -> int:
        """0 = Sunday .. 6 = Saturday, derived from the current date."""
        y, m, d = self.safe_date_parts()
        python_weekday = datetime.date(y, m, d).weekday()   # Monday=0 .. Sunday=6
        return (python_weekday + 1) % 7

    def weekday_glyph_name(self) -> str:
        return reg.LETTER_BANKS["week"][self.weekday_index()]

    def month_glyph_name(self) -> str:
        _, m, _ = self.safe_date_parts()
        return reg.LETTER_BANKS["month"][m - 1]

    def apm_glyph_name(self) -> str:
        return "en_pm" if self.is_pm() else "en_am"
