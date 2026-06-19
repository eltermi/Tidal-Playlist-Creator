from __future__ import annotations

from collections.abc import Callable

from services.models import PlaylistSummary, TrackMatch, TrackStatus


class PlaylistCreator:
    def __init__(self, tidal_client: object) -> None:
        self.tidal_client = tidal_client

    def create(
        self,
        name: str,
        description: str,
        matches: list[TrackMatch],
        progress: Callable[[int, int], None] | None = None,
    ) -> PlaylistSummary:
        selected_matches = [
            match for match in matches if match.use and match.selected is not None
        ]
        track_ids = [match.selected.track_id for match in selected_matches]

        summary = PlaylistSummary(
            found=sum(match.selected is not None for match in matches),
            skipped=sum(not match.use and match.selected is not None for match in matches),
            not_found=sum(match.selected is None for match in matches),
            playlist_name=name,
        )

        playlist = self.tidal_client.create_playlist(
            name,
            description,
            track_ids,
            progress=progress,
        )
        summary.added = len(track_ids)
        summary.playlist_url = (
            getattr(playlist, "share_url", "")
            or getattr(playlist, "listen_url", "")
            or ""
        )

        for match in matches:
            if match.selected is None:
                match.status = TrackStatus.NOT_FOUND
            elif not match.use:
                match.status = TrackStatus.SKIPPED
            else:
                match.status = TrackStatus.ADDED
        return summary
