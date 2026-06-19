from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QThreadPool, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.models import PlaylistSummary, TrackMatch
from services.playlist_creator import PlaylistCreator
from services.report_generator import save_report
from services.search_engine import SearchEngine, clean_song_list
from services.tidal_client import TidalClient
from ui.dialogs import LoginDialog, ManualReviewDialog
from ui.workers import TaskWorker


class MainWindow(QMainWindow):
    COL_USE = 0
    COL_QUERY = 1
    COL_RESULT = 2
    COL_ARTIST = 3
    COL_ALBUM = 4
    COL_CONFIDENCE = 5

    def __init__(self, tidal_client: TidalClient | None = None) -> None:
        super().__init__()
        self.matches: list[TrackMatch] = []
        self.summary: PlaylistSummary | None = None
        self.busy = False
        self._workers: set[TaskWorker] = set()

        data_dir = Path(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        self.tidal_client = tidal_client or TidalClient(
            data_dir / "tidal_session.json"
        )
        self.search_engine = SearchEngine(self.tidal_client)
        self.playlist_creator = PlaylistCreator(self.tidal_client)

        self.setWindowTitle("Tidal Playlist Creator")
        self.resize(1120, 780)
        self.setMinimumSize(860, 620)
        self._build_ui()
        self._connect_signals()
        self._set_authenticated(False)
        self._restore_login()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Tidal Playlist Creator")
        title.setObjectName("title")
        subtitle = QLabel("Turn a pasted song list into a TIDAL playlist.")
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        self.login_status = QLabel("Not connected")
        self.login_status.setObjectName("muted")
        self.login_button = QPushButton("Connect TIDAL")
        header.addWidget(self.login_status)
        header.addWidget(self.login_button)
        root.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        input_card = QFrame()
        input_card.setObjectName("card")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Lebensfreude")
        self.description_input = QPlainTextEdit()
        self.description_input.setPlaceholderText(
            "Strauss, Vivaldi and other uplifting classical pieces…"
        )
        self.description_input.setMaximumHeight(76)
        self.songs_input = QPlainTextEdit()
        self.songs_input.setPlaceholderText(
            "Johann Strauss II – Kaiser-Walzer\n"
            "Antonio Vivaldi – La Primavera\n"
            "Mozart – Eine kleine Nachtmusik"
        )
        form.addRow("Playlist Name", self.name_input)
        form.addRow("Playlist Description", self.description_input)
        form.addRow("Songs", self.songs_input)
        input_layout.addLayout(form)

        input_buttons = QHBoxLayout()
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.setObjectName("primaryButton")
        self.clear_button = QPushButton("Clear")
        input_buttons.addWidget(self.analyze_button)
        input_buttons.addWidget(self.clear_button)
        input_buttons.addStretch()
        input_layout.addLayout(input_buttons)
        splitter.addWidget(input_card)

        results_card = QFrame()
        results_card.setObjectName("card")
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(12, 12, 12, 12)
        results_header = QHBoxLayout()
        results_title = QLabel("Validation")
        results_title.setObjectName("sectionTitle")
        self.results_info = QLabel("Analyze a song list to see matches.")
        self.results_info.setObjectName("muted")
        results_header.addWidget(results_title)
        results_header.addWidget(self.results_info)
        results_header.addStretch()
        results_layout.addLayout(results_header)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                "Use",
                "Original Query",
                "Selected Result",
                "Artist",
                "Album",
                "Confidence %",
            ]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_USE, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_QUERY, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_RESULT, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_ARTIST, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_ALBUM, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_CONFIDENCE, QHeaderView.ResizeMode.ResizeToContents
        )
        results_layout.addWidget(self.table)

        action_row = QHBoxLayout()
        self.review_button = QPushButton("Review Unchecked")
        self.create_button = QPushButton("Create Playlist")
        self.create_button.setObjectName("primaryButton")
        self.report_button = QPushButton("Save Report")
        action_row.addWidget(self.review_button)
        action_row.addStretch()
        action_row.addWidget(self.report_button)
        action_row.addWidget(self.create_button)
        results_layout.addLayout(action_row)
        splitter.addWidget(results_card)
        splitter.setSizes([320, 420])
        root.addWidget(splitter, 1)

        status_row = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("muted")
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setMaximumWidth(260)
        self.progress.hide()
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_row.addWidget(self.progress)
        root.addLayout(status_row)

        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        self.login_button.clicked.connect(self._login_or_logout)
        self.analyze_button.clicked.connect(self._analyze)
        self.clear_button.clicked.connect(self._clear)
        self.review_button.clicked.connect(self._review_unchecked)
        self.create_button.clicked.connect(self._create_playlist)
        self.report_button.clicked.connect(self._save_report)
        self.table.itemChanged.connect(self._use_changed)
        self.table.cellDoubleClicked.connect(self._review_row)

    def _restore_login(self) -> None:
        if not self.tidal_client.has_saved_session:
            self._set_authenticated(False)
            self._set_busy(False, "Ready")
            return

        self._set_busy(True, "Checking saved TIDAL session…")
        worker = TaskWorker(self._restore_login_task)
        worker.signals.result.connect(self._set_authenticated)
        worker.signals.error.connect(lambda _message: self._set_authenticated(False))
        worker.signals.finished.connect(lambda: self._set_busy(False, "Ready"))
        self._start_worker(worker)

    def _restore_login_task(self, progress_callback=None) -> bool:
        return self.tidal_client.restore_session()

    def _login_or_logout(self) -> None:
        if self.tidal_client.is_authenticated:
            answer = QMessageBox.question(
                self,
                "Disconnect TIDAL",
                "Remove the locally saved TIDAL session?",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.tidal_client.logout()
                self._set_authenticated(False)
            return

        dialog = LoginDialog(self.tidal_client, self)
        dialog.authenticated.connect(lambda: self._set_authenticated(True))
        dialog.exec()

    def _set_authenticated(self, authenticated: bool) -> None:
        self.login_status.setText("Connected" if authenticated else "Not connected")
        self.login_button.setText("Disconnect" if authenticated else "Connect TIDAL")
        self.analyze_button.setEnabled(authenticated and not self.busy)
        self._update_action_states()

    def _ensure_authenticated(self) -> bool:
        if self.tidal_client.is_authenticated:
            return True
        QMessageBox.information(
            self,
            "TIDAL Login Required",
            "Connect your TIDAL account before continuing.",
        )
        self._login_or_logout()
        return self.tidal_client.is_authenticated

    def _analyze(self) -> None:
        if not self._ensure_authenticated():
            return
        queries = clean_song_list(self.songs_input.toPlainText())
        if not queries:
            QMessageBox.warning(self, "No Songs", "Paste at least one song.")
            return

        self.matches = []
        self.summary = None
        self.table.setRowCount(0)
        self._set_busy(True, f"Analyzing 0 of {len(queries)}…", len(queries))
        worker = TaskWorker(self._analyze_task, queries)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.result.connect(self._analysis_complete)
        worker.signals.error.connect(self._show_error)
        worker.signals.finished.connect(lambda: self._set_busy(False, "Ready"))
        self._start_worker(worker)

    def _analyze_task(self, queries: list[str], progress_callback=None):
        matches = []
        for index, query in enumerate(queries, start=1):
            try:
                match = self.search_engine.search_one(query)
            except Exception as exc:
                from services.models import TrackMatch, TrackStatus

                match = TrackMatch(
                    original_query=query,
                    selected=None,
                    use=False,
                    confidence=0,
                    status=TrackStatus.NOT_FOUND,
                    error=str(exc),
                )
            matches.append(match)
            if progress_callback:
                progress_callback(index, len(queries), f"Analyzing {index} of {len(queries)}…")
        return matches

    def _analysis_complete(self, matches: list[TrackMatch]) -> None:
        self.matches = matches
        self._populate_table()
        found = sum(match.selected is not None for match in matches)
        self.results_info.setText(f"{found} of {len(matches)} tracks found.")
        self._update_action_states()

    def _populate_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.matches))
        for row, match in enumerate(self.matches):
            use_item = QTableWidgetItem()
            use_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            use_item.setCheckState(
                Qt.CheckState.Checked
                if match.use and match.selected
                else Qt.CheckState.Unchecked
            )
            self.table.setItem(row, self.COL_USE, use_item)
            self.table.setItem(
                row, self.COL_QUERY, QTableWidgetItem(match.original_query)
            )

            candidate = match.selected
            values = (
                candidate.title if candidate else "Not found",
                candidate.artist if candidate else "",
                candidate.album if candidate else "",
                f"{match.confidence}%",
            )
            for column, value in enumerate(values, start=self.COL_RESULT):
                item = QTableWidgetItem(value)
                self.table.setItem(row, column, item)

            color = self._confidence_color(match.confidence)
            for column in range(self.COL_RESULT, self.COL_CONFIDENCE + 1):
                self.table.item(row, column).setBackground(color)
            self.table.setRowHeight(row, 36)
        self.table.blockSignals(False)

    @staticmethod
    def _confidence_color(confidence: int) -> QColor:
        if confidence >= 90:
            return QColor("#dff4e5")
        if confidence >= 75:
            return QColor("#fff1c7")
        return QColor("#fde2e1")

    def _use_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != self.COL_USE or item.row() >= len(self.matches):
            return
        self.matches[item.row()].use = item.checkState() == Qt.CheckState.Checked
        self._update_action_states()

    def _review_unchecked(self) -> None:
        rows = [
            row
            for row, match in enumerate(self.matches)
            if not match.use or match.selected is None
        ]
        if not rows:
            QMessageBox.information(
                self, "Review", "There are no unchecked tracks to review."
            )
            return
        for row in rows:
            self._review_row(row, 0)

    def _review_row(self, row: int, _column: int) -> None:
        if row < 0 or row >= len(self.matches):
            return
        dialog = ManualReviewDialog(
            self.matches[row],
            self.tidal_client,
            self,
        )
        if dialog.exec():
            self._populate_table()
            self._update_action_states()

    def _create_playlist(self) -> None:
        if not self._ensure_authenticated():
            return
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Playlist Name", "Enter a name for the playlist."
            )
            self.name_input.setFocus()
            return
        selected = [
            match for match in self.matches if match.use and match.selected is not None
        ]
        if not selected:
            QMessageBox.warning(
                self, "No Tracks", "Select at least one matched track."
            )
            return

        self._set_busy(True, "Creating playlist…", len(selected))
        worker = TaskWorker(
            self._create_task,
            name,
            self.description_input.toPlainText().strip(),
        )
        worker.signals.progress.connect(self._on_progress)
        worker.signals.result.connect(self._playlist_created)
        worker.signals.error.connect(self._show_error)
        worker.signals.finished.connect(lambda: self._set_busy(False, "Ready"))
        self._start_worker(worker)

    def _create_task(self, name: str, description: str, progress_callback=None):
        def progress(current: int, total: int) -> None:
            if progress_callback:
                progress_callback(current, total, f"Adding {current} of {total}…")

        return self.playlist_creator.create(
            name,
            description,
            self.matches,
            progress=progress,
        )

    def _playlist_created(self, summary: PlaylistSummary) -> None:
        self.summary = summary
        self._populate_table()
        self.results_info.setText(
            f"Found {summary.found} · Added {summary.added} · "
            f"Skipped {summary.skipped} · Not found {summary.not_found}"
        )
        message = (
            "Playlist created successfully.\n\n"
            f"{summary.added} tracks added.\n"
            f"{summary.skipped} skipped.\n"
            f"{summary.not_found} not found."
        )
        box = QMessageBox(self)
        box.setWindowTitle("Playlist Created")
        box.setText(message)
        open_button = None
        if summary.playlist_url:
            open_button = box.addButton(
                "Open in TIDAL", QMessageBox.ButtonRole.ActionRole
            )
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if open_button and box.clickedButton() is open_button:
            QDesktopServices.openUrl(QUrl(summary.playlist_url))
        self._update_action_states()

    def _save_report(self) -> None:
        if not self.matches:
            return
        default_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Playlist Report",
            str(Path(default_dir) / "playlist_report.txt"),
            "Text files (*.txt)",
        )
        if not path:
            return
        try:
            save_report(path, self.matches, self.summary)
            self.status_label.setText(f"Report saved to {path}")
        except OSError as exc:
            self._show_error(str(exc))

    def _clear(self) -> None:
        self.name_input.clear()
        self.description_input.clear()
        self.songs_input.clear()
        self.matches = []
        self.summary = None
        self.table.setRowCount(0)
        self.results_info.setText("Analyze a song list to see matches.")
        self._update_action_states()

    def _set_busy(
        self,
        busy: bool,
        message: str,
        maximum: int | None = None,
    ) -> None:
        self.busy = busy
        self.status_label.setText(message)
        self.progress.setVisible(busy)
        if busy:
            if maximum:
                self.progress.setRange(0, maximum)
                self.progress.setValue(0)
            else:
                self.progress.setRange(0, 0)
        self.login_button.setEnabled(not busy)
        self.clear_button.setEnabled(not busy)
        self.analyze_button.setEnabled(
            not busy and self.tidal_client.is_authenticated
        )
        self._update_action_states()

    def _on_progress(self, current: int, total: int, message: str) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.status_label.setText(message)

    def _update_action_states(self) -> None:
        has_matches = bool(self.matches)
        has_selected = any(
            match.use and match.selected is not None for match in self.matches
        )
        self.review_button.setEnabled(has_matches and not self.busy)
        self.report_button.setEnabled(has_matches and not self.busy)
        self.create_button.setEnabled(
            has_selected
            and not self.busy
            and self.tidal_client.is_authenticated
        )

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Tidal Playlist Creator", message)

    def _start_worker(self, worker: TaskWorker) -> None:
        self._workers.add(worker)
        worker.signals.finished.connect(
            lambda current=worker: self._workers.discard(current)
        )
        QThreadPool.globalInstance().start(worker)
