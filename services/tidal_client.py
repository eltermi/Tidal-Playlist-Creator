from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import tidalapi
from requests import Session as RequestsSession

from services.models import TrackCandidate

LOGGER = logging.getLogger(__name__)


class TidalClientError(RuntimeError):
    pass


class AuthenticationRequired(TidalClientError):
    pass


class TidalClient:
    def __init__(self, session_path: Path, request_timeout: float = 15.0) -> None:
        self.session_path = session_path
        self.request_timeout = request_timeout
        self._authenticated = False
        self.session = self._new_session()

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    @property
    def has_saved_session(self) -> bool:
        return self.session_path.is_file()

    def restore_session(self) -> bool:
        if not self.has_saved_session:
            self._authenticated = False
            return False
        try:
            loaded = self.session.load_session_from_file(self.session_path)
            self._authenticated = bool(loaded)
            if self._authenticated:
                self._persist_session()
                return True
        except Exception:
            LOGGER.exception("Could not restore the saved TIDAL session")
        self._authenticated = False
        return False

    def begin_login(self):
        return self.session.login_oauth()

    def finish_login(self) -> bool:
        self._authenticated = bool(
            self.session.user is not None
            and self.session.user.id
            and self.session.session_id
        )
        if not self._authenticated:
            return False
        self._persist_session()
        return True

    def _persist_session(self) -> None:
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.session.save_session_to_file(self.session_path)
        try:
            self.session_path.chmod(0o600)
        except OSError:
            LOGGER.warning("Could not restrict session file permissions")

    def logout(self) -> None:
        self._authenticated = False
        self.session = self._new_session()
        try:
            self.session_path.unlink(missing_ok=True)
        except OSError as exc:
            raise TidalClientError(f"Could not remove the saved session: {exc}") from exc

    def search_tracks(self, query: str, limit: int = 8) -> list[TrackCandidate]:
        self._require_authentication()
        try:
            results = self.session.search(
                query,
                models=[tidalapi.media.Track],
                limit=limit,
            )
            return [self._to_candidate(track) for track in results.get("tracks", [])]
        except Exception as exc:
            raise TidalClientError(f"TIDAL search failed for “{query}”: {exc}") from exc

    def create_playlist(
        self,
        name: str,
        description: str,
        track_ids: list[int],
        progress: Callable[[int, int], None] | None = None,
    ):
        self._require_authentication()
        if self.session.user is None:
            raise AuthenticationRequired("No authenticated TIDAL user is available.")

        try:
            playlist = self.session.user.create_playlist(name, description)
            total = len(track_ids)
            batch_size = 100
            for start in range(0, total, batch_size):
                batch = track_ids[start : start + batch_size]
                playlist.add(batch)
                if progress:
                    progress(min(start + len(batch), total), total)
            return playlist
        except Exception as exc:
            raise TidalClientError(f"Could not create the playlist: {exc}") from exc

    def _require_authentication(self) -> None:
        if not self.is_authenticated:
            raise AuthenticationRequired("TIDAL authentication is required.")

    def _new_session(self) -> tidalapi.Session:
        session = tidalapi.Session()
        request_session = RequestsSession()
        original_request = request_session.request

        def request_with_timeout(method, url, **kwargs):
            kwargs.setdefault("timeout", self.request_timeout)
            return original_request(method, url, **kwargs)

        request_session.request = request_with_timeout
        session.request_session = request_session
        return session

    @staticmethod
    def _to_candidate(track) -> TrackCandidate:
        artist = getattr(getattr(track, "artist", None), "name", "") or ""
        if not artist:
            artists = getattr(track, "artists", None) or []
            artist = ", ".join(
                item.name for item in artists if getattr(item, "name", None)
            )
        album = getattr(getattr(track, "album", None), "name", "") or ""
        return TrackCandidate(
            track_id=int(track.id),
            title=track.name or "",
            artist=artist,
            album=album,
            raw_track=track,
        )
