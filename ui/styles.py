APP_STYLESHEET = """
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue";
    font-size: 13px;
    color: #202124;
}
QMainWindow, QDialog {
    background: #f5f6f8;
}
QFrame#card {
    background: white;
    border: 1px solid #dfe2e7;
    border-radius: 10px;
}
QLabel#title {
    font-size: 24px;
    font-weight: 650;
}
QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 600;
}
QLabel#muted {
    color: #68707c;
}
QLineEdit, QTextEdit, QPlainTextEdit, QTableWidget {
    background: white;
    border: 1px solid #cfd4dc;
    border-radius: 7px;
    padding: 7px;
    selection-background-color: #3f7cff;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #3f7cff;
}
QPushButton {
    min-height: 30px;
    padding: 2px 14px;
    border-radius: 7px;
    border: 1px solid #c8cdd5;
    background: #ffffff;
}
QPushButton:hover {
    background: #f0f3f7;
}
QPushButton:pressed {
    background: #e6eaf0;
}
QPushButton:disabled {
    color: #9ba1aa;
    background: #f2f3f5;
}
QPushButton#primaryButton {
    color: white;
    border-color: #2f6fe7;
    background: #3578f6;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background: #2468e6;
}
QHeaderView::section {
    background: #f2f4f7;
    border: none;
    border-bottom: 1px solid #d9dde4;
    padding: 8px;
    font-weight: 600;
}
QTableWidget {
    gridline-color: #e6e9ee;
}
QProgressBar {
    border: none;
    border-radius: 4px;
    background: #e4e7ec;
    height: 8px;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 4px;
    background: #3578f6;
}
"""
