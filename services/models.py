from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TrackStatus(str, Enum):
    FOUND = "found"
    SKIPPED = "skipped"
    NOT_FOUND = "not_found"
    ADDED = "added"
    FAILED = "failed"


@dataclass(slots=True)
class TrackCandidate:
    track_id: int
    title: str
    artist: str
    album: str
    raw_track: Any = field(default=None, repr=False, compare=False)

    @property
    def display_name(self) -> str:
        return f"{self.title} — {self.artist}"


@dataclass(slots=True)
class TrackMatch:
    original_query: str
    selected: TrackCandidate | None = None
    alternatives: list[TrackCandidate] = field(default_factory=list)
    confidence: int = 0
    use: bool = True
    status: TrackStatus = TrackStatus.FOUND
    error: str = ""

    @property
    def is_found(self) -> bool:
        return self.selected is not None


@dataclass(slots=True)
class PlaylistSummary:
    found: int = 0
    added: int = 0
    skipped: int = 0
    not_found: int = 0
    failed: int = 0
    playlist_name: str = ""
    playlist_url: str = ""
