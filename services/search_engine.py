from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Iterable

from services.models import TrackCandidate, TrackMatch, TrackStatus


LEADING_MARKER_RE = re.compile(
    r"""^\s*(?:
        (?:\d+|[A-Za-z])[\.\)\]:-]\s*
        |[-–—•●▪◦*]+\s*
        |[✓✔☑✅☐□]\s*
    )+""",
    re.VERBOSE,
)
WHITESPACE_RE = re.compile(r"\s+")
SEPARATOR_RE = re.compile(r"\s*[-–—:|]\s*")
NON_WORD_RE = re.compile(r"[^\w\s]", re.UNICODE)


def clean_song_line(line: str) -> str:
    cleaned = LEADING_MARKER_RE.sub("", line)
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def clean_song_list(text: str) -> list[str]:
    songs: list[str] = []
    for line in text.splitlines():
        cleaned = clean_song_line(line)
        if cleaned:
            songs.append(cleaned)
    return songs


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.casefold()
    value = SEPARATOR_RE.sub(" ", value)
    value = NON_WORD_RE.sub(" ", value)
    return WHITESPACE_RE.sub(" ", value).strip()


def confidence_score(query: str, candidate: TrackCandidate) -> int:
    normalized_query = normalize_text(query)
    title = normalize_text(candidate.title)
    artist = normalize_text(candidate.artist)
    combined = normalize_text(f"{candidate.artist} {candidate.title}")

    if not normalized_query or not title:
        return 0

    title_ratio = SequenceMatcher(None, normalized_query, title).ratio()
    combined_ratio = SequenceMatcher(None, normalized_query, combined).ratio()

    query_tokens = set(normalized_query.split())
    result_tokens = set(f"{title} {artist}".split())
    token_overlap = (
        len(query_tokens & result_tokens) / len(query_tokens) if query_tokens else 0
    )

    contains_bonus = 0.08 if title in normalized_query or normalized_query in title else 0
    score = max(title_ratio, combined_ratio) * 0.62 + token_overlap * 0.38
    return max(0, min(100, round((score + contains_bonus) * 100)))


class SearchEngine:
    def __init__(self, tidal_client: object) -> None:
        self.tidal_client = tidal_client

    def search_one(self, query: str, limit: int = 8) -> TrackMatch:
        candidates = self.tidal_client.search_tracks(query, limit=limit)
        if not candidates:
            return TrackMatch(
                original_query=query,
                selected=None,
                alternatives=[],
                confidence=0,
                use=False,
                status=TrackStatus.NOT_FOUND,
            )

        selected = candidates[0]
        return TrackMatch(
            original_query=query,
            selected=selected,
            alternatives=candidates,
            confidence=confidence_score(query, selected),
            use=True,
            status=TrackStatus.FOUND,
        )

    def analyze(self, queries: Iterable[str]) -> list[TrackMatch]:
        return [self.search_one(query) for query in queries]
