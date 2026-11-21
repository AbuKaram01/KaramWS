# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The history of the jobs that ended: what was asked, where it went and how it ended.

A small JSON file in the user's data folder. It is read and written whole (a few hundred short entries at most) and
written atomically, so a crash never leaves it half-written.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .paths import data_dir

OUTCOMES = ("done", "stopped", "error")


@dataclass(frozen=True)
class HistoryEntry:
    id: str
    started_at: str  # ISO 8601, UTC
    url: str
    kind: str  # "auto", "article", "section" or "site"
    output_dir: str
    saved: int
    skipped: int
    failed: int
    outcome: str  # one of OUTCOMES


def new_entry(
    url: str, kind: str, output_dir: str, saved: int, skipped: int, failed: int, outcome: str,
) -> HistoryEntry:
    """An entry for a job that ended just now."""
    return HistoryEntry(
        id=uuid.uuid4().hex[:12],
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        url=url, kind=kind, output_dir=output_dir, saved=saved, skipped=skipped, failed=failed, outcome=outcome,
    )


class HistoryStore:
    def __init__(self, path: Path | None = None):
        self._path = path or data_dir() / "history.json"

    def entries(self) -> list[HistoryEntry]:
        """Every entry, the newest first. A damaged file is set aside and gives an empty history."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("not a list")
        except FileNotFoundError:
            return []
        except (OSError, ValueError):
            self._set_aside()
            return []
        found = [entry for entry in map(_entry_from, data) if entry is not None]
        return sorted(found, key=lambda entry: entry.started_at, reverse=True)

    def add(self, entry: HistoryEntry, keep: int) -> None:
        """Add an entry and drop the oldest ones beyond ``keep``."""
        kept = [entry, *self.entries()][:keep]
        self._write(kept)

    def delete(self, entry_id: str) -> None:
        self._write([entry for entry in self.entries() if entry.id != entry_id])

    def clear(self) -> None:
        self._write([])

    def _write(self, entries: list[HistoryEntry]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(self._path.name + ".tmp")
        saved = json.dumps([asdict(entry) for entry in entries], indent=2, ensure_ascii=False)
        temporary.write_text(saved, encoding="utf-8")
        os.replace(temporary, self._path)

    def _set_aside(self) -> None:
        try:
            os.replace(self._path, self._path.with_name(self._path.name + ".broken"))
        except OSError:
            pass


def _entry_from(data) -> HistoryEntry | None:
    """An entry from its saved form, or None when it is not one (a hand-edited file)."""
    try:
        entry = HistoryEntry(**data)
    except (TypeError, ValueError):
        return None
    texts = (entry.id, entry.started_at, entry.url, entry.kind, entry.output_dir, entry.outcome)
    counts = (entry.saved, entry.skipped, entry.failed)
    valid = all(isinstance(text, str) for text in texts) and all(
        isinstance(count, int) and not isinstance(count, bool) for count in counts
    )
    return entry if valid else None
