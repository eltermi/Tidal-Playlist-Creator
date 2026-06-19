from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.styles import APP_STYLESHEET


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    QCoreApplication.setOrganizationName("eltermi")
    QCoreApplication.setApplicationName("Tidal Playlist Creator")
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, True)

    app = QApplication(sys.argv)
    app.setApplicationDisplayName("Tidal Playlist Creator")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
