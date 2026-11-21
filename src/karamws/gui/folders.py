# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Where the articles are saved by default, and the dialog to choose another folder."""

from collections.abc import Callable
from pathlib import Path

from gi.repository import GLib, Gtk

from ..config import AppConfig


def default_output_dir() -> Path:
    """Documents/Articles (wherever the system keeps the Documents folder), else the home folder."""
    documents = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
    return Path(documents or Path.home()) / "Articles"


def saved_output_dir(config: AppConfig) -> Path:
    """The folder the user chose last time, or the default one."""
    return Path(config.output_dir) if config.output_dir.strip() else default_output_dir()


def choose_folder(parent: Gtk.Widget, on_chosen: Callable[[Path], None]) -> None:
    """Ask the user for a folder; ``on_chosen`` is called with it (and not at all when the dialog is closed)."""

    def finished(dialog: Gtk.FileDialog, result) -> None:
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return  # the dialog was closed without choosing
        on_chosen(Path(folder.get_path()))

    Gtk.FileDialog(title="Save Articles To").select_folder(parent.get_root(), None, finished)
