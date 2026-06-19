from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import tidalapi
from requests import Session as RequestsSession

from services.models import PlaylistInfo, PlaylistTrack, TrackCandidate

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

    def list_user_playlists(self) -> list[PlaylistInfo]:
        self._require_authentication()
        if self.session.user is None:
            raise AuthenticationRequired("No authenticated TIDAL user is available.")

        try:
            playlists = self.session.user.playlists()
            result = []
            for playlist in playlists:
                creator = getattr(playlist, "creator", None)
                if creator is None or creator.id != self.session.user.id:
                    continue
                if not isinstance(playlist, tidalapi.playlist.UserPlaylist):
                    continue
                result.append(self._to_playlist_info(playlist))
            return sorted(result, key=lambda item: item.name.strip().casefold())
        except Exception as exc:
            raise TidalClientError(f"Could not load your playlists: {exc}") from exc

    def get_playlist_tracks(self, playlist_id: str) -> list[PlaylistTrack]:
        playlist = self._get_editable_playlist(playlist_id)
        try:
            return [
                self._to_playlist_track(track)
                for track in playlist.tracks_paginated()
            ]
        except Exception as exc:
            raise TidalClientError(f"Could not load playlist tracks: {exc}") from exc

    def add_tracks_to_playlist(
        self,
        playlist_id: str,
        track_ids: list[int],
        allow_duplicates: bool = False,
        progress: Callable[[int, int], None] | None = None,
    ) -> tuple[int, int, int]:
        playlist = self._get_editable_playlist(playlist_id)
        existing_ids = {
            int(track.id) for track in playlist.tracks_paginated()
        }
        requested_ids = list(dict.fromkeys(int(track_id) for track_id in track_ids))
        if allow_duplicates:
            pending_ids = [int(track_id) for track_id in track_ids]
            already_present = 0
        else:
            pending_ids = [
                track_id for track_id in requested_ids if track_id not in existing_ids
            ]
            already_present = len(requested_ids) - len(pending_ids)

        added = 0
        failed = 0
        total = len(pending_ids)
        for start in range(0, total, 100):
            batch = pending_ids[start : start + 100]
            try:
                batch_added = len(
                    playlist.add(batch, allow_duplicates=allow_duplicates, limit=100)
                )
            except Exception:
                LOGGER.warning("Retrying playlist update after refreshing the playlist")
                try:
                    playlist = self._get_editable_playlist(playlist_id)
                    batch_added = len(
                        playlist.add(
                            batch,
                            allow_duplicates=allow_duplicates,
                            limit=100,
                        )
                    )
                except Exception:
                    LOGGER.exception("Could not add a playlist batch after retry")
                    batch_added = 0
            added += batch_added
            failed += len(batch) - batch_added
            if progress:
                progress(min(start + len(batch), total), total)
        return added, already_present, failed

    def _require_authentication(self) -> None:
        if not self.is_authenticated:
            raise AuthenticationRequired("TIDAL authentication is required.")

    def _get_editable_playlist(self, playlist_id: str):
        self._require_authentication()
        if self.session.user is None:
            raise AuthenticationRequired("No authenticated TIDAL user is available.")
        try:
            playlist = self.session.playlist(playlist_id)
        except Exception as exc:
            raise TidalClientError(f"Could not load the selected playlist: {exc}") from exc
        creator = getattr(playlist, "creator", None)
        if (
            not isinstance(playlist, tidalapi.playlist.UserPlaylist)
            or creator is None
            or creator.id != self.session.user.id
        ):
            raise TidalClientError("The selected playlist is not editable by this user.")
        return playlist

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

    @staticmethod
    def _to_playlist_info(playlist) -> PlaylistInfo:
        return PlaylistInfo(
            playlist_id=str(playlist.id),
            name=playlist.name or "Untitled Playlist",
            description=playlist.description or "",
            track_count=max(0, int(playlist.num_tracks)),
            playlist_url=playlist.share_url or playlist.listen_url or "",
        )

    @staticmethod
    def _to_playlist_track(track) -> PlaylistTrack:
        artist = getattr(getattr(track, "artist", None), "name", "") or ""
        if not artist:
            artists = getattr(track, "artists", None) or []
            artist = ", ".join(
                item.name for item in artists if getattr(item, "name", None)
            )
        return PlaylistTrack(
            track_id=int(track.id),
            title=track.name or "",
            artist=artist,
            album=getattr(getattr(track, "album", None), "name", "") or "",
            duration_seconds=int(getattr(track, "duration", 0) or 0),
        )
