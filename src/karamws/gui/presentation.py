# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Wording and icons for the window. Pure functions, no GTK, so they are easy to test."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..core import ScrapeEvent, ScrapeStatus
from ..core.history import HistoryEntry

_ICONS = {
    ScrapeStatus.SAVED: "object-select-symbolic",
    ScrapeStatus.SKIPPED: "media-skip-forward-symbolic",
    ScrapeStatus.FAILED: "dialog-warning-symbolic",
}


_OUTCOME_ICONS = {
    "done": "object-select-symbolic",
    "stopped": "media-playback-stop-symbolic",
    "error": "dialog-warning-symbolic",
}
_OUTCOME_LABELS = {"done": "", "stopped": " · Stopped", "error": " · Stopped by an error"}


@dataclass(frozen=True)
class EventRow:
    title: str
    subtitle: str
    icon_name: str


def describe_event(event: ScrapeEvent) -> EventRow:
    return EventRow(event.url, _subtitle(event), _ICONS[event.status])


def summarize(counts: Counter[ScrapeStatus]) -> str:
    return (
        f"Saved {counts[ScrapeStatus.SAVED]} · "
        f"Skipped {counts[ScrapeStatus.SKIPPED]} · "
        f"Failed {counts[ScrapeStatus.FAILED]}"
    )


def job_outcome(cancelled: bool, error: str | None) -> str:
    """How a job ended, as the history records it: ``done``, ``stopped`` or ``error``."""
    if error:
        return "error"
    return "stopped" if cancelled else "done"


def format_when(iso_time: str) -> str:
    """A time saved in the history (UTC, ISO 8601) as the user's local date and time."""
    try:
        return datetime.fromisoformat(iso_time).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso_time


def describe_history_entry(entry: HistoryEntry) -> EventRow:
    """The row of a finished job in the history: its link, when and how it went."""
    counts = Counter({
        ScrapeStatus.SAVED: entry.saved, ScrapeStatus.SKIPPED: entry.skipped, ScrapeStatus.FAILED: entry.failed,
    })
    subtitle = f"{format_when(entry.started_at)} · {summarize(counts)}{_OUTCOME_LABELS.get(entry.outcome, '')}"
    return EventRow(entry.url, subtitle, _OUTCOME_ICONS.get(entry.outcome, _OUTCOME_ICONS["done"]))


def finish_headline(cancelled: bool, error: str | None) -> str:
    if error:
        return f"Stopped by an error: {error}"
    return "Stopped" if cancelled else "Done"


def finish_notification(headline: str, counts: Counter[ScrapeStatus]) -> tuple[str, str]:
    """The title and the text of the desktop notification shown when a job ends."""
    return f"KaramWS: {headline}", summarize(counts)


def display_path(path: Path, home: Path) -> str:
    """Show paths the way a file manager does: ~/Documents/Articles."""
    try:
        return f"~/{path.relative_to(home)}"
    except ValueError:
        return str(path)


def _subtitle(event: ScrapeEvent) -> str:
    if event.status is ScrapeStatus.SAVED:
        return Path(event.detail).name
    if event.status is ScrapeStatus.SKIPPED:
        return "Already saved"
    return event.detail
