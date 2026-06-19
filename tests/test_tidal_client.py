from pathlib import Path

from services.tidal_client import TidalClient


def test_new_client_is_not_authenticated_without_network(tmp_path: Path):
    client = TidalClient(tmp_path / "missing-session.json")

    assert client.is_authenticated is False
    assert client.has_saved_session is False
    assert client.restore_session() is False


def test_authentication_state_is_cached(tmp_path: Path):
    client = TidalClient(tmp_path / "missing-session.json")

    def fail_if_called():
        raise AssertionError("check_login must not be called by the UI state property")

    client.session.check_login = fail_if_called
    assert client.is_authenticated is False


def test_add_tracks_filters_existing_tracks_and_batches(tmp_path: Path):
    client = TidalClient(tmp_path / "session.json")

    class Track:
        def __init__(self, track_id):
            self.id = track_id

    class Playlist:
        def __init__(self):
            self.batches = []

        def tracks_paginated(self):
            return [Track(1)]

        def add(self, track_ids, allow_duplicates=False, limit=100):
            self.batches.append(track_ids)
            return track_ids

    playlist = Playlist()
    client._get_editable_playlist = lambda _playlist_id: playlist

    added, already_present, failed = client.add_tracks_to_playlist(
        "playlist-id",
        [1, *range(2, 104)],
    )

    assert added == 102
    assert already_present == 1
    assert failed == 0
    assert [len(batch) for batch in playlist.batches] == [100, 2]


def test_add_tracks_reports_failed_batch_after_retry(tmp_path: Path):
    client = TidalClient(tmp_path / "session.json")

    class Playlist:
        def tracks_paginated(self):
            return []

        def add(self, track_ids, allow_duplicates=False, limit=100):
            raise RuntimeError("temporary failure")

    client._get_editable_playlist = lambda _playlist_id: Playlist()

    added, already_present, failed = client.add_tracks_to_playlist(
        "playlist-id",
        [10, 11],
    )

    assert added == 0
    assert already_present == 0
    assert failed == 2
