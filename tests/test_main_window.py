from pathlib import Path

from PySide6.QtWidgets import QApplication

from services.tidal_client import TidalClient
from ui.main_window import MainWindow


def test_first_launch_is_ready_and_connect_button_is_enabled(
    tmp_path: Path,
):
    app = QApplication.instance() or QApplication([])
    client = TidalClient(tmp_path / "missing-session.json")

    window = MainWindow(tidal_client=client)

    assert window.status_label.text() == "Ready"
    assert window.progress.isHidden()
    assert window.login_button.isEnabled()
    assert window.login_button.text() == "Connect TIDAL"
    assert not window.analyze_button.isEnabled()
    window.close()
    app.processEvents()
