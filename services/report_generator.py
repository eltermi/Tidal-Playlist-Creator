from __future__ import annotations

from pathlib import Path

from services.models import PlaylistSummary, TrackMatch, TrackStatus


def generate_report(
    matches: list[TrackMatch],
    summary: PlaylistSummary | None = None,
) -> str:
    lines = ["Tidal Playlist Creator Report", "=" * 29, ""]

    if summary:
        lines.extend(
            [
                f"Playlist: {summary.playlist_name}",
                f"Found: {summary.found}",
                f"Added: {summary.added}",
                f"Skipped: {summary.skipped}",
                f"Not Found: {summary.not_found}",
                "",
            ]
        )

    for match in matches:
        if match.status == TrackStatus.ADDED:
            marker = "✓"
        elif match.selected is None or match.status in {
            TrackStatus.NOT_FOUND,
            TrackStatus.FAILED,
        }:
            marker = "✗"
        else:
            marker = "–"

        line = f"{marker} {match.original_query}"
        if match.selected is not None:
            line += f" -> {match.selected.title} — {match.selected.artist}"
        if match.error:
            line += f" ({match.error})"
        lines.append(line)

    return "\n".join(lines) + "\n"


def save_report(
    path: str | Path,
    matches: list[TrackMatch],
    summary: PlaylistSummary | None = None,
) -> None:
    Path(path).write_text(generate_report(matches, summary), encoding="utf-8")
