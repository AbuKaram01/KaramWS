# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The history of the jobs that ended: run one again, open its folder, or forget it."""

from collections.abc import Callable

from gi.repository import Adw, Gtk

from ..core.history import HistoryEntry, HistoryStore
from .presentation import describe_history_entry
from .widgets import confirm_clear_history

_PAGE_EMPTY, _PAGE_LIST = "empty", "list"


def _icon_button(icon_name: str, tooltip: str, on_clicked: Callable[[], None]) -> Gtk.Button:
    button = Gtk.Button(icon_name=icon_name, tooltip_text=tooltip, valign=Gtk.Align.CENTER, css_classes=["flat"])
    button.connect("clicked", lambda _button: on_clicked())
    return button


class HistoryDialog(Adw.Dialog):
    """The list of finished jobs, the newest first.

    Args:
        history: Where the jobs are kept.
        on_use_again: Called with an entry when the user wants to run it again. Returns whether it was applied (it
            is not while a job is running); the dialog closes when it was.
        on_open_folder: Called with the folder of an entry.
    """

    def __init__(
        self,
        history: HistoryStore,
        on_use_again: Callable[[HistoryEntry], bool],
        on_open_folder: Callable[[str], None],
    ) -> None:
        super().__init__(title="History", content_width=520, content_height=560)
        self._history = history
        self._on_use_again = on_use_again
        self._on_open_folder = on_open_folder
        self._rows: list[Adw.ActionRow] = []

        self._list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"], margin_top=12,
                                 margin_bottom=12, margin_start=12, margin_end=12, valign=Gtk.Align.START)
        self._stack = Gtk.Stack(vexpand=True)
        self._stack.add_named(
            Adw.StatusPage(icon_name="view-list-symbolic", title="No History Yet",
                           description="Jobs you run show up here, so you can run them again."),
            _PAGE_EMPTY,
        )
        self._stack.add_named(Gtk.ScrolledWindow(child=Adw.Clamp(child=self._list, maximum_size=600)), _PAGE_LIST)

        self._clear_button = Gtk.Button(label="Clear", css_classes=["flat"])
        self._clear_button.connect("clicked", lambda _button: confirm_clear_history(self, self._clear))
        header = Adw.HeaderBar()
        header.pack_start(self._clear_button)
        toolbar = Adw.ToolbarView(content=Adw.ToastOverlay(child=self._stack))
        toolbar.add_top_bar(header)
        self.set_child(toolbar)
        self.refresh()

    def refresh(self) -> None:
        """Show the history as it is now."""
        for row in self._rows:
            self._list.remove(row)
        self._rows.clear()
        entries = self._history.entries()
        for entry in entries:
            row = self._build_row(entry)
            self._list.append(row)
            self._rows.append(row)
        self._stack.set_visible_child_name(_PAGE_LIST if entries else _PAGE_EMPTY)
        self._clear_button.set_sensitive(bool(entries))

    def _build_row(self, entry: HistoryEntry) -> Adw.ActionRow:
        shown = describe_history_entry(entry)
        row = Adw.ActionRow(
            title=shown.title, subtitle=shown.subtitle, use_markup=False, title_lines=1, subtitle_lines=1,
            tooltip_text=f"{entry.url}\n{entry.output_dir}",
        )
        row.add_prefix(Gtk.Image.new_from_icon_name(shown.icon_name))
        row.add_suffix(_icon_button("view-refresh-symbolic", "Use this link again", lambda: self._use(entry)))
        open_folder = lambda: self._on_open_folder(entry.output_dir)  # noqa: E731
        row.add_suffix(_icon_button("folder-open-symbolic", "Open the folder", open_folder))
        row.add_suffix(_icon_button("user-trash-symbolic", "Remove from the history", lambda: self._forget(entry)))
        return row

    def _use(self, entry: HistoryEntry) -> None:
        if self._on_use_again(entry):
            self.close()

    def _forget(self, entry: HistoryEntry) -> None:
        self._history.delete(entry.id)
        self.refresh()

    def _clear(self) -> None:
        self._history.clear()
        self.refresh()
