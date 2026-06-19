from __future__ import annotations

from urllib.parse import urlparse

from PySide6.QtCore import QSettings, QSize, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from services.models import TrackCandidate, TrackMatch, TrackStatus
from services.search_engine import confidence_score
from ui.workers import TaskWorker


def normalize_external_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if not parsed.scheme:
        return f"https://{value.lstrip('/')}"
    if parsed.scheme not in {"http", "https"}:
        return ""
    return value


class LoginDialog(QDialog):
    authenticated = Signal()

    def __init__(self, tidal_client, parent=None) -> None:
        super().__init__(parent)
        self.tidal_client = tidal_client
        self.future = None
        self.login_url = ""
        self._worker: TaskWorker | None = None
        self.setWindowTitle("Connect to TIDAL")
        self.setModal(True)
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        title = QLabel("Connect your TIDAL account")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.instructions = QLabel(
            "A secure TIDAL authorization page will open in your default browser. "
            "This application never receives or stores your password."
        )
        self.instructions.setWordWrap(True)
        layout.addWidget(self.instructions)

        self.url_label = QLabel()
        self.url_label.setWordWrap(True)
        self.url_label.setTextInteractionFlags(
            self.url_label.textInteractionFlags()
            | self.url_label.textInteractionFlags().TextSelectableByMouse
        )
        layout.addWidget(self.url_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.open_button = QPushButton("Open TIDAL Login")
        self.open_button.setObjectName("primaryButton")
        self.copy_button = QPushButton("Copy Link")
        self.copy_button.setEnabled(False)
        buttons.addButton(self.open_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(self.copy_button, QDialogButtonBox.ButtonRole.ActionRole)
        self.open_button.clicked.connect(self.start_login)
        self.copy_button.clicked.connect(self._copy_login_url)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def start_login(self) -> None:
        if self.login_url:
            self._open_login_url()
            return

        self.open_button.setEnabled(False)
        try:
            login, self.future = self.tidal_client.begin_login()
        except Exception as exc:
            QMessageBox.critical(self, "TIDAL Login", str(exc))
            self.open_button.setEnabled(True)
            return

        self.login_url = normalize_external_url(login.verification_uri_complete)
        if not self.login_url:
            self._login_failed("TIDAL returned an invalid authorization link.")
            return

        self.url_label.setText(
            f"Waiting for authorization…\n{self.login_url}"
        )
        self.open_button.setText("Open Login Page")
        self.open_button.setEnabled(True)
        self.copy_button.setEnabled(True)

        self._worker = TaskWorker(self._wait_for_login)
        self._worker.signals.result.connect(self._login_complete)
        self._worker.signals.error.connect(self._login_failed)
        self._worker.signals.finished.connect(self._worker_finished)
        QThreadPool.globalInstance().start(self._worker)
        self._open_login_url()

    def _open_login_url(self) -> None:
        if not QDesktopServices.openUrl(QUrl(self.login_url)):
            QMessageBox.warning(
                self,
                "Open TIDAL Login",
                "The browser could not be opened. Copy the link and paste it "
                "into your browser.",
            )

    def _copy_login_url(self) -> None:
        if self.login_url:
            QGuiApplication.clipboard().setText(self.login_url)
            self.copy_button.setText("Copied")

    def _wait_for_login(self, progress_callback=None) -> bool:
        self.future.result()
        return self.tidal_client.finish_login()

    def _login_complete(self, success: bool) -> None:
        if not success:
            self._login_failed("TIDAL did not confirm the login.")
            return
        self.authenticated.emit()
        self.accept()

    def _login_failed(self, message: str) -> None:
        self.open_button.setEnabled(True)
        QMessageBox.critical(self, "TIDAL Login", message)

    def _worker_finished(self) -> None:
        self._worker = None


class ManualReviewDialog(QDialog):
    SIZE_KEY = "manual_review/size"
    POSITION_KEY = "manual_review/position"

    def __init__(self, match: TrackMatch, tidal_client, parent=None) -> None:
        super().__init__(parent)
        self.match = match
        self.tidal_client = tidal_client
        self.selected_candidate: TrackCandidate | None = None
        self._worker: TaskWorker | None = None
        self.button_group = QButtonGroup(self)

        self.setWindowTitle("Review Track")
        self.setMinimumSize(560, 400)
        self.setSizeGripEnabled(True)
        settings = QSettings()
        saved_size = settings.value(self.SIZE_KEY)
        saved_position = settings.value(self.POSITION_KEY)
        self.resize(saved_size if saved_size is not None else QSize(760, 560))
        if saved_position is not None:
            self.move(saved_position)
        layout = QVBoxLayout(self)

        title = QLabel(match.original_query)
        title.setObjectName("sectionTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        search_row = QHBoxLayout()
        self.search_field = QLineEdit(match.original_query)
        self.search_button = QPushButton("Search Again")
        search_row.addWidget(self.search_field, 1)
        search_row.addWidget(self.search_button)
        layout.addLayout(search_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.search_button.clicked.connect(self._search_again)
        self._show_candidates(match.alternatives)

    def _show_candidates(self, candidates: list[TrackCandidate]) -> None:
        current_size = self.size()
        content = QWidget()
        content_layout = QVBoxLayout(content)
        self.button_group = QButtonGroup(self)
        self.button_group.buttonClicked.connect(lambda: self.ok_button.setEnabled(True))

        for candidate in candidates:
            radio = QRadioButton(
                f"{candidate.title}\n{candidate.artist} · {candidate.album}"
            )
            radio.setProperty("candidate", candidate)
            self.button_group.addButton(radio)
            content_layout.addWidget(radio)

        if not candidates:
            content_layout.addWidget(QLabel("No alternatives found."))
        content_layout.addStretch()
        self.scroll.setWidget(content)
        self.ok_button.setEnabled(False)
        QTimer.singleShot(0, lambda size=current_size: self.resize(size))

    def _search_again(self) -> None:
        query = self.search_field.text().strip()
        if not query:
            return
        self.search_button.setEnabled(False)
        self._worker = TaskWorker(self._perform_search, query)
        self._worker.signals.result.connect(self._show_candidates)
        self._worker.signals.error.connect(
            lambda message: QMessageBox.critical(self, "Search Failed", message)
        )
        self._worker.signals.finished.connect(self._search_finished)
        QThreadPool.globalInstance().start(self._worker)

    def _search_finished(self) -> None:
        self.search_button.setEnabled(True)
        self._worker = None

    def _perform_search(self, query: str, progress_callback=None):
        return self.tidal_client.search_tracks(query, limit=12)

    def _accept_selection(self) -> None:
        selected = self.button_group.checkedButton()
        if selected is None:
            return
        candidate = selected.property("candidate")
        self.match.selected = candidate
        self.match.alternatives = [
            button.property("candidate") for button in self.button_group.buttons()
        ]
        self.match.confidence = confidence_score(
            self.match.original_query,
            candidate,
        )
        self.match.use = True
        self.match.status = TrackStatus.FOUND
        self.selected_candidate = candidate
        self.accept()

    def done(self, result: int) -> None:
        settings = QSettings()
        settings.setValue(self.SIZE_KEY, self.size())
        settings.setValue(self.POSITION_KEY, self.pos())
        super().done(result)
