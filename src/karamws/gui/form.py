# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The part of the window where the user says what to save: a link, what kind of link it is, and a folder.

Everything else (limits, pauses, the browser, notifications) lives in Preferences.
"""

from collections.abc import Callable
from pathlib import Path

from gi.repository import Adw, Gtk

from ..config import AppConfig, update_saved_config
from ..core import UrlKind
from .folders import choose_folder, saved_output_dir
from .presentation import display_path
from .request import ScrapeRequest, normalize_url

_KIND_CHOICES: list[tuple[str, UrlKind | None]] = [
    ("Detect automatically", None),
    ("A single article", UrlKind.ARTICLE),
    ("A section or category", UrlKind.SECTION),
    ("A whole website", UrlKind.SITE),
]


class LinkForm(Gtk.Box):
    def __init__(self, on_submit: Callable[[], None]):
        """`on_submit` is called when the user presses Enter in the link field."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self._output_dir = saved_output_dir(AppConfig.load())

        self._url = Adw.EntryRow(title="Link to an article, section or website")
        self._url.set_input_purpose(Gtk.InputPurpose.URL)
        self._url.connect("entry-activated", lambda _row: on_submit())
        self._url.connect("changed", lambda row: row.remove_css_class("error"))

        self._kind = Adw.ComboRow(title="This link is")
        self._kind.set_model(Gtk.StringList.new([label for label, _ in _KIND_CHOICES]))

        self._folder = Adw.ActionRow(title="Save articles to", use_markup=False)
        self._folder.add_suffix(self._folder_button())
        self._show_output_dir()

        self.append(_group(self._url))
        self.append(_group(self._kind, self._folder))

    def build_request(self) -> ScrapeRequest | None:
        """Read the form and the saved settings. Returns None (and flags the link field) when the link is unusable."""
        url = normalize_url(self._url.get_text())
        if url is None:
            self._url.add_css_class("error")
            self._url.grab_focus()
            return None
        kind = _KIND_CHOICES[self._kind.get_selected()][1]
        return ScrapeRequest(url, kind, self._output_dir, AppConfig.load().scraper_config())

    def set_fields(self, url: str, kind: UrlKind | None, output_dir: Path) -> None:
        """Fill the form, for example from an entry of the history."""
        self._url.set_text(url)
        self._kind.set_selected([choice for _, choice in _KIND_CHOICES].index(kind))
        self._set_output_dir(output_dir)

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    def set_busy(self, busy: bool) -> None:
        self.set_sensitive(not busy)

    def _folder_button(self) -> Gtk.Button:
        button = Gtk.Button(
            icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER, tooltip_text="Choose a folder",
            css_classes=["flat"],
        )
        button.connect("clicked", lambda _button: choose_folder(self, self._on_folder_chosen))
        return button

    def _on_folder_chosen(self, folder: Path) -> None:
        self._set_output_dir(folder)
        update_saved_config(output_dir=str(folder))  # the next start opens with it

    def _set_output_dir(self, folder: Path) -> None:
        self._output_dir = folder
        self._show_output_dir()

    def _show_output_dir(self) -> None:
        self._folder.set_subtitle(display_path(self._output_dir, Path.home()))


def _group(*rows: Gtk.Widget) -> Adw.PreferencesGroup:
    group = Adw.PreferencesGroup()
    for row in rows:
        group.add(row)
    return group
