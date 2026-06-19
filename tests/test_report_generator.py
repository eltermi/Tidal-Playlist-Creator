from services.models import (
    PlaylistSummary,
    TrackCandidate,
    TrackMatch,
    TrackStatus,
)
from services.report_generator import generate_report


def test_generate_report_contains_summary_and_track_statuses():
    found = TrackMatch(
        "Artist – Song",
        TrackCandidate(1, "Song", "Artist", "Album"),
        status=TrackStatus.ADDED,
    )
    missing = TrackMatch(
        "Unknown Track",
        selected=None,
        use=False,
        status=TrackStatus.NOT_FOUND,
    )
    report = generate_report(
        [found, missing],
        PlaylistSummary(
            found=1,
            added=1,
            not_found=1,
            playlist_name="Test",
        ),
    )
    assert "Playlist: Test" in report
    assert "✓ Artist – Song" in report
    assert "✗ Unknown Track" in report
