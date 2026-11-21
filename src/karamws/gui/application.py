# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The Adw.Application of KaramWS and the ``main`` entry point of the graphical interface.

The application owns what outlives a single window (the Chromium download, the history of jobs) and the actions of the
main menu, so that every window and dialog reaches them in the same way.
"""

import sys
from pathlib import Path

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .. import APP_ID, __version__
from ..core.history import HistoryStore
from .browser_download import BrowserDownloads
from .window import MainWindow

APP_NAME = "KaramWS"
WEBSITE = "https://github.com/AbuKaram01/KaramWS"
_PACKAGE_DIR = Path(__file__).resolve().parent


class Application(Adw.Application):
    """The KaramWS application: creates the main window and owns what is shared between dialogs.

    Attributes:
        browser_downloads: The Chromium download, which goes on when the dialog that started it is closed.
        history: The history of the jobs that ended.
        preferences_dialog: The Preferences dialog while it is open, otherwise None.
        welcome_dialog: The welcome guide while it is open, otherwise None.
    """

    def __init__(self) -> None:
        # The name that notifications and the system show for the program (otherwise it is "python").
        GLib.set_application_name(APP_NAME)
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.browser_downloads = BrowserDownloads()
        self.history = HistoryStore()
        self.preferences_dialog = None
        self.welcome_dialog = None
        self._create_action("quit", lambda *_: self.quit(), ["<primary>q"])
        self._create_action("about", self._on_about_action)
        self._create_action("preferences", self._on_preferences_action, ["<primary>comma"])
        self._create_action("download-browser", self._on_preferences_action)
        self._create_action("welcome", self._on_welcome_action)
        self._create_action("history", self._on_history_action, ["<primary>h"])
        # What clicking a "job finished" notification runs: bring the window back.
        self._create_action("show-window", lambda *_: self.activate())

    def do_startup(self) -> None:
        """Make the application icon findable by the icon theme."""
        Adw.Application.do_startup(self)
        # The icon is not installed system-wide when running from a source checkout, and Windows has no
        # system-wide icon folders at all: look next to the sources and in the environment's own share/icons.
        display = Gdk.Display.get_default()
        if display is not None:
            theme = Gtk.IconTheme.get_for_display(display)
            for icons in (_PACKAGE_DIR.parents[2] / "data" / "icons", Path(sys.prefix) / "share" / "icons"):
                if icons.is_dir():
                    theme.add_search_path(str(icons))
            Gtk.Window.set_default_icon_name(APP_ID)

    def do_activate(self) -> None:
        """Show the main window, creating it first if needed; on the very first start, also the welcome guide."""
        window = self.props.active_window
        first_start = window is None
        if not window:
            window = MainWindow(self)
        window.present()
        if first_start:
            self._show_welcome_if_new()

    # --- The welcome guide ---

    def _show_welcome_if_new(self) -> None:
        """Open the welcome guide on the very first start."""
        from .welcome import should_show_welcome

        if should_show_welcome():
            def open_once() -> bool:
                self._open_welcome()
                return GLib.SOURCE_REMOVE

            # After the main window is on screen, so the guide opens on top of it.
            GLib.idle_add(open_once)

    def _open_welcome(self):
        """Open the welcome guide on top of the main window (the one already open stays)."""
        from .welcome import WelcomeDialog

        if self.welcome_dialog is None:
            dialog = WelcomeDialog(self.browser_downloads, app_icon=APP_ID)
            dialog.connect("closed", lambda _dialog: setattr(self, "welcome_dialog", None))
            self.welcome_dialog = dialog
            dialog.present(self.props.active_window)
        return self.welcome_dialog

    def _on_welcome_action(self, *_args) -> None:
        self._open_welcome()

    # --- The other menu actions ---

    def _on_preferences_action(self, *_args) -> None:
        """Open Preferences (the browser, with its Download button, is the first group in it)."""
        from .preferences import PreferencesDialog

        if self.preferences_dialog is None:
            dialog = PreferencesDialog(self.browser_downloads, self.history)
            dialog.connect("closed", lambda _dialog: setattr(self, "preferences_dialog", None))
            self.preferences_dialog = dialog
            dialog.present(self.props.active_window)

    def _on_history_action(self, *_args) -> None:
        window = self.props.active_window
        if isinstance(window, MainWindow):
            window.show_history()

    def _on_about_action(self, *_args) -> None:
        about = Adw.AboutDialog(
            application_name=APP_NAME,
            application_icon=APP_ID,
            version=__version__,
            developer_name="AbuKaram01",
            developers=["AbuKaram01"],
            copyright="© 2026 AbuKaram01",
            comments="Save the articles of a page, a section or a whole website as Markdown files.",
            website=WEBSITE,
            issue_url=f"{WEBSITE}/issues",
            license_type=Gtk.License.AGPL_3_0,
        )
        about.present(self.props.active_window)

    def _create_action(self, name: str, callback, shortcuts: list[str] | None = None) -> None:
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main() -> int:
    """Run the application and return its exit status."""
    return Application().run(sys.argv)
