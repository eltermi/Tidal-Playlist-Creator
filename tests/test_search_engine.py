from services.models import TrackCandidate
from services.search_engine import (
    clean_song_line,
    clean_song_list,
    confidence_score,
)


def test_clean_song_line_removes_common_markers():
    assert clean_song_line("1. Kaiser-Walzer") == "Kaiser-Walzer"
    assert clean_song_line("- Kaiser-Walzer") == "Kaiser-Walzer"
    assert clean_song_line("✓ Kaiser-Walzer") == "Kaiser-Walzer"
    assert clean_song_line("  •   Kaiser-Walzer  ") == "Kaiser-Walzer"


def test_clean_song_list_removes_blank_lines():
    assert clean_song_list("\n1. One\n\n- Two\n") == ["One", "Two"]


def test_confidence_score_rewards_title_and_artist_match():
    exact = TrackCandidate(1, "Kaiser-Walzer", "Johann Strauss II", "Strauss")
    unrelated = TrackCandidate(2, "Blue Monday", "New Order", "Power")
    query = "Johann Strauss II – Kaiser-Walzer"
    assert confidence_score(query, exact) >= 90
    assert confidence_score(query, unrelated) < 50
