# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Live progress: a status line and one row per article."""

from collections import Counter
from collections.abc import Callable

from gi.repository import Adw, Gtk

from ..core import ScrapeEvent, ScrapeStatus

from .presentation import EventRow, describe_event, summarize

_MAX_VISIBLE_ROWS = 500
_LIST_MIN_HEIGHT = 240
_SEARCHING_MESSAGE = "Looking for articles…"
_STOPPING_MESSAGE = "Stopping after the current article…"


class ResultsView(Gtk.Box):
    def __init__(self, on_open_folder: Callable[[], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12, vexpand=True)
        self._counts: Counter[ScrapeStatus] = Counter()
        self._rows: list[Adw.ActionRow] = []

        self._spinner = Gtk.Spinner()
        self._status = Gtk.Label(xalign=0, hexpand=True, wrap=True)
        self._open_button = Gtk.Button(label="Open Folder", valign=Gtk.Align.CENTER)
        self._open_button.connect("clicked", lambda _button: on_open_folder())
        self._list = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"]
        )

        status_line = Gtk.Box(spacing=12)
        for widget in (self._spinner, self._status, self._open_button):
            status_line.append(widget)
        self.append(status_line)
        self.append(
            Gtk.ScrolledWindow(
                child=self._list,
                vexpand=True,
                min_content_height=_LIST_MIN_HEIGHT,
                hscrollbar_policy=Gtk.PolicyType.NEVER,
            )
        )
        self.set_visible(False)

    def start(self) -> None:
        self._counts.clear()
        for row in self._rows:
            self._list.remove(row)
        self._rows.clear()
        self._status.set_text(_SEARCHING_MESSAGE)
        self._spinner.set_visible(True)
        self._spinner.start()
        self._open_button.set_visible(False)
        self.set_visible(True)

    def add(self, event: ScrapeEvent) -> None:
        self._counts[event.status] += 1
        row = _build_row(describe_event(event))
        self._list.prepend(row)
        self._rows.append(row)
        if len(self._rows) > _MAX_VISIBLE_ROWS:
            self._list.remove(self._rows.pop(0))
        self._status.set_text(summarize(self._counts))

    @property
    def counts(self) -> Counter[ScrapeStatus]:
        """How many articles were saved, skipped and failed so far (a copy)."""
        return Counter(self._counts)

    def show_stopping(self) -> None:
        self._status.set_text(_STOPPING_MESSAGE)

    def finish(self, headline: str) -> None:
        self._spinner.stop()
        self._spinner.set_visible(False)
        self._status.set_text(f"{headline} · {summarize(self._counts)}")
        self._open_button.set_visible(self._counts[ScrapeStatus.SAVED] > 0)


def _build_row(row: EventRow) -> Adw.ActionRow:
    widget = Adw.ActionRow(
        title=row.title,
        subtitle=row.subtitle,
        use_markup=False,
        title_lines=1,
        subtitle_lines=1,
        tooltip_text=f"{row.title}\n{row.subtitle}",
    )
    widget.add_prefix(Gtk.Image.new_from_icon_name(row.icon_name))
    return widget
