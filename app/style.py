"""Modern dark stylesheet for VFWatchfaceFactory."""

STYLESHEET = """
QWidget {
    background-color: #1e1f24;
    color: #e6e6e9;
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #17181c;
}

QMenuBar {
    background-color: #17181c;
    border-bottom: 1px solid #2a2c33;
}
QMenuBar::item {
    padding: 6px 12px;
    background: transparent;
}
QMenuBar::item:selected {
    background: #2d6cdf;
    border-radius: 4px;
}
QMenu {
    background-color: #22242b;
    border: 1px solid #34363f;
}
QMenu::item {
    padding: 6px 24px;
}
QMenu::item:selected {
    background-color: #2d6cdf;
}

QGroupBox {
    background-color: #23252c;
    border: 1px solid #34363f;
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #9fb4e0;
}

QLabel { background: transparent; }

QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit {
    background-color: #14151a;
    border: 1px solid #34363f;
    border-radius: 5px;
    padding: 4px 6px;
    selection-background-color: #2d6cdf;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {
    border: 1px solid #4d8dfd;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #22242b;
    border: 1px solid #34363f;
    selection-background-color: #2d6cdf;
}

QPushButton {
    background-color: #2b2d35;
    border: 1px solid #3c3e48;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton:hover {
    background-color: #33363f;
    border: 1px solid #4d8dfd;
}
QPushButton:pressed {
    background-color: #22242b;
}
QPushButton:disabled {
    color: #6a6c74;
    background-color: #202127;
}

QPushButton#primaryButton {
    background-color: #2d6cdf;
    border: 1px solid #2d6cdf;
    color: white;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background-color: #4d8dfd;
}

QTableWidget {
    background-color: #14151a;
    border: 1px solid #34363f;
    gridline-color: #2a2c33;
}
QHeaderView::section {
    background-color: #22242b;
    color: #c7cad3;
    padding: 4px;
    border: none;
    border-right: 1px solid #34363f;
}

QTabWidget::pane {
    border: 1px solid #34363f;
    border-radius: 6px;
}
QTabBar::tab {
    background: #22242b;
    padding: 6px 14px;
    border: 1px solid #34363f;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #2d6cdf;
    color: white;
}

QGraphicsView {
    background-color: #0c0c0f;
    border: 1px solid #34363f;
    border-radius: 6px;
}

QScrollBar:vertical {
    background: #17181c;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3c3e48;
    border-radius: 6px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #4d8dfd; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #17181c;
    height: 12px;
}
QScrollBar::handle:horizontal {
    background: #3c3e48;
    border-radius: 6px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #4d8dfd; }

QStatusBar {
    background-color: #17181c;
    border-top: 1px solid #2a2c33;
}

QSplitter::handle {
    background-color: #2a2c33;
}
"""
