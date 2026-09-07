#!/usr/bin/env python3
"""VFWatchfaceFactory entry point."""
import sys

from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.style import STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
