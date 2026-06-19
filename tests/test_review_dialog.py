from PySide6.QtCore import QCoreApplication, QSettings, QSize
from PySide6.QtWidgets import QApplication

from services.models import TrackCandidate, TrackMatch
from ui.dialogs import ManualReviewDialog


class FakeTidalClient:
    pass


def test_review_dialog_keeps_size_when_candidates_change(tmp_path):
    app = QApplication.instance() or QApplication([])
    QCoreApplication.setOrganizationName("test")
    QCoreApplication.setApplicationName("tidal-review-dialog-test")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path),
    )
    QSettings().clear()

    match = TrackMatch(
        "Artist – Song",
        alternatives=[TrackCandidate(1, "Song", "Artist", "Album")],
    )
    dialog = ManualReviewDialog(match, FakeTidalClient())
    expected = QSize(900, 700)
    dialog.resize(expected)

    dialog._show_candidates(
        [
            TrackCandidate(index, f"Song {index}", "Artist", "Album")
            for index in range(20)
        ]
    )
    app.processEvents()

    assert dialog.size() == expected
    dialog.reject()


def test_review_dialog_restores_saved_geometry(tmp_path):
    app = QApplication.instance() or QApplication([])
    QCoreApplication.setOrganizationName("test")
    QCoreApplication.setApplicationName("tidal-review-dialog-restore-test")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path),
    )
    QSettings().clear()

    match = TrackMatch("Artist – Song")
    first = ManualReviewDialog(match, FakeTidalClient())
    first.resize(880, 640)
    first.reject()

    second = ManualReviewDialog(match, FakeTidalClient())
    assert second.size() == QSize(880, 640)
    second.reject()
    app.processEvents()
