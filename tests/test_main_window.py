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


def test_update_mode_shows_existing_playlist_controls(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    client = TidalClient(tmp_path / "missing-session.json")
    window = MainWindow(tidal_client=client)

    window.update_mode_radio.setChecked(True)
    app.processEvents()

    assert not window.existing_playlist_panel.isHidden()
    assert not window.name_input.isVisible()
    assert not window.description_input.isVisible()
    assert window.create_button.text() == "Add to Playlist"
    window.close()
