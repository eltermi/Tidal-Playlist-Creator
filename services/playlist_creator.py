from __future__ import annotations

from collections.abc import Callable

from services.models import (
    PlaylistOperationResult,
    PlaylistSummary,
    PlaylistTrack,
    TrackMatch,
    TrackStatus,
)


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

    @staticmethod
    def mark_existing(
        matches: list[TrackMatch],
        existing_tracks: list[PlaylistTrack],
        allow_duplicates: bool = False,
    ) -> None:
        seen_ids = {track.track_id for track in existing_tracks}
        for match in matches:
            if match.selected is None:
                continue
            if not allow_duplicates and match.selected.track_id in seen_ids:
                match.use = False
                match.status = TrackStatus.ALREADY_PRESENT
            else:
                seen_ids.add(match.selected.track_id)
            if allow_duplicates and match.status == TrackStatus.ALREADY_PRESENT:
                match.use = True
                match.status = TrackStatus.FOUND

    def append(
        self,
        playlist_id: str,
        playlist_name: str,
        playlist_url: str,
        matches: list[TrackMatch],
        allow_duplicates: bool = False,
        progress: Callable[[int, int], None] | None = None,
    ) -> PlaylistOperationResult:
        selected_matches = [
            match for match in matches if match.use and match.selected is not None
        ]
        track_ids = [match.selected.track_id for match in selected_matches]
        added, already_present_at_write, failed = (
            self.tidal_client.add_tracks_to_playlist(
                playlist_id,
                track_ids,
                allow_duplicates=allow_duplicates,
                progress=progress,
            )
        )

        already_present = sum(
            match.status == TrackStatus.ALREADY_PRESENT for match in matches
        ) + already_present_at_write
        summary = PlaylistSummary(
            found=sum(match.selected is not None for match in matches),
            added=added,
            already_present=already_present,
            skipped=sum(
                not match.use
                and match.selected is not None
                and match.status != TrackStatus.ALREADY_PRESENT
                for match in matches
            ),
            not_found=sum(match.selected is None for match in matches),
            failed=failed,
            playlist_name=playlist_name,
            playlist_url=playlist_url,
            operation="update",
        )

        for match in matches:
            if match.selected is None:
                match.status = TrackStatus.NOT_FOUND
            elif match.status == TrackStatus.ALREADY_PRESENT:
                continue
            elif not match.use:
                match.status = TrackStatus.SKIPPED
            else:
                match.status = TrackStatus.ADDED

        tracks = self.tidal_client.get_playlist_tracks(playlist_id)
        return PlaylistOperationResult(summary=summary, tracks=tracks)
