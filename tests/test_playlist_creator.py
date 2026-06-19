from services.models import (
    PlaylistTrack,
    TrackCandidate,
    TrackMatch,
    TrackStatus,
)
from services.playlist_creator import PlaylistCreator


class FakeTidalClient:
    def __init__(self):
        self.added_track_ids = []

    def add_tracks_to_playlist(
        self,
        playlist_id,
        track_ids,
        allow_duplicates=False,
        progress=None,
    ):
        self.added_track_ids = track_ids
        if progress:
            progress(len(track_ids), len(track_ids))
        return len(track_ids), 0, 0

    def get_playlist_tracks(self, playlist_id):
        return [
            PlaylistTrack(1, "Existing", "Artist", "Album", 180),
            PlaylistTrack(2, "New", "Artist", "Album", 200),
        ]


def test_mark_existing_disables_playlist_and_input_duplicates():
    matches = [
        TrackMatch("Existing", TrackCandidate(1, "Existing", "Artist", "Album")),
        TrackMatch("New", TrackCandidate(2, "New", "Artist", "Album")),
        TrackMatch("New again", TrackCandidate(2, "New", "Artist", "Album")),
    ]

    PlaylistCreator.mark_existing(
        matches,
        [PlaylistTrack(1, "Existing", "Artist", "Album")],
    )

    assert matches[0].status == TrackStatus.ALREADY_PRESENT
    assert matches[0].use is False
    assert matches[1].status == TrackStatus.FOUND
    assert matches[1].use is True
    assert matches[2].status == TrackStatus.ALREADY_PRESENT
    assert matches[2].use is False


def test_append_updates_playlist_and_returns_refreshed_tracks():
    client = FakeTidalClient()
    creator = PlaylistCreator(client)
    matches = [
        TrackMatch("New", TrackCandidate(2, "New", "Artist", "Album")),
        TrackMatch(
            "Existing",
            TrackCandidate(1, "Existing", "Artist", "Album"),
            use=False,
            status=TrackStatus.ALREADY_PRESENT,
        ),
    ]

    result = creator.append(
        "playlist-id",
        "My Playlist",
        "https://tidal.com/playlist/playlist-id",
        matches,
    )

    assert client.added_track_ids == [2]
    assert result.summary.added == 1
    assert result.summary.already_present == 1
    assert result.summary.operation == "update"
    assert len(result.tracks) == 2
