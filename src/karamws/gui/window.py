# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The main window: ties the form, the Start/Stop button, the results and the worker together."""

from pathlib import Path

from gi.repository import Adw, Gio, Gtk

from .. import winsupport
from ..config import AppConfig
from ..core import ScrapeStatus, UrlKind
from ..core.history import HistoryEntry, new_entry
from .form import LinkForm
from .history_dialog import HistoryDialog
from .presentation import finish_headline, finish_notification, job_outcome
from .request import ScrapeRequest
from .results import ResultsView
from .worker import ScrapeWorker

_WINDOW_WIDTH = 560
_WINDOW_HEIGHT = 780
_CONTENT_MAX_WIDTH = 640
_NOTIFICATION_ID = "scrape-finished"

# The entries of the header-bar menu as (label, application action). The application defines the actions.
_MENU_ITEMS = [
    ("Download Browser…", "app.download-browser"),
    ("History", "app.history"),
    ("Preferences", "app.preferences"),
    ("Welcome Guide", "app.welcome"),
    ("About", "app.about"),
]


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application):
        super().__init__(
            application=application,
            title="KaramWS",
            default_width=_WINDOW_WIDTH,
            default_height=_WINDOW_HEIGHT,
        )
        self._worker: ScrapeWorker | None = None
        self._request: ScrapeRequest | None = None
        self._history_dialog: HistoryDialog | None = None

        self._form = LinkForm(on_submit=self._on_action_clicked)
        self._results = ResultsView(on_open_folder=self._open_output_folder)
        self._action_button = Gtk.Button(halign=Gtk.Align.CENTER)
        self._action_button.connect("clicked", lambda _button: self._on_action_clicked())
        self._show_start_button()

        self._toasts = Adw.ToastOverlay(child=self._build_layout())
        self.set_content(self._toasts)
        self.connect("close-request", self._on_close_request)
        # GTK 4 has no icon API on Windows: the title bar and the taskbar get the icon of the program otherwise.
        self.connect("map", lambda *_: winsupport.apply_icon_to_own_windows())

    # --- Building ---

    def _build_layout(self) -> Adw.ToolbarView:
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
            vexpand=True,
            margin_top=24,
            margin_bottom=24,
            margin_start=12,
            margin_end=12,
        )
        for widget in (self._form, self._action_button, self._results):
            content.append(widget)
        scroller = Gtk.ScrolledWindow(
            child=Adw.Clamp(child=content, maximum_size=_CONTENT_MAX_WIDTH),
            hscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        view = Adw.ToolbarView(content=scroller)
        view.add_top_bar(self._build_header())
        return view

    @staticmethod
    def _build_header() -> Adw.HeaderBar:
        menu = Gio.Menu()
        for label, action in _MENU_ITEMS:
            menu.append(label, action)
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text="Main Menu", primary=True)
        menu_button.set_menu_model(menu)
        header = Adw.HeaderBar()
        header.pack_end(menu_button)
        return header

    # --- Used by the application's menu actions ---

    def show_toast(self, message: str) -> None:
        self._toasts.add_toast(Adw.Toast(title=message))

    def show_history(self) -> None:
        """Open the history of finished jobs (the one already open stays)."""
        if self._history_dialog is None:
            dialog = HistoryDialog(self.get_application().history, self._use_history_entry, self._open_folder)
            dialog.connect("closed", lambda _dialog: setattr(self, "_history_dialog", None))
            self._history_dialog = dialog
            dialog.present(self)

    # --- Running a job ---

    def _on_action_clicked(self) -> None:
        if self._worker is None:
            self._start()
        else:
            self._stop()

    def _start(self) -> None:
        request = self._form.build_request()
        if request is None:
            return
        self._request = request
        self._form.set_busy(True)
        self._results.start()
        self._show_stop_button()
        self._worker = ScrapeWorker(request, self._results.add, self._on_finished)
        self._worker.start()

    def _stop(self) -> None:
        self._worker.cancel()
        self._action_button.set_sensitive(False)
        self._results.show_stopping()

    def _on_finished(self, error: str | None) -> None:
        cancelled = self._worker.cancelled
        headline = finish_headline(cancelled, error)
        self._worker = None
        self._form.set_busy(False)
        self._show_start_button()
        self._results.finish(headline)
        config = AppConfig.load()
        self._record_in_history(config, job_outcome(cancelled, error))
        if config.notify_when_done:
            self._notify_finished(*finish_notification(headline, self._results.counts))

    def _record_in_history(self, config: AppConfig, outcome: str) -> None:
        counts = self._results.counts
        total = sum(counts.values())
        if not config.history_enabled or total == 0:
            return
        request = self._request
        entry = new_entry(
            request.url, request.kind.value if request.kind else "auto", str(request.output_dir),
            counts[ScrapeStatus.SAVED], counts[ScrapeStatus.SKIPPED], counts[ScrapeStatus.FAILED], outcome,
        )
        self.get_application().history.add(entry, config.history_keep)
        if self._history_dialog is not None:
            self._history_dialog.refresh()

    def _use_history_entry(self, entry: HistoryEntry) -> bool:
        """Put an entry of the history back in the form. Not while a job is running."""
        if self._worker is not None:
            self.show_toast("Wait for the current job to finish.")
            return False
        kind = None if entry.kind == "auto" else UrlKind(entry.kind)
        self._form.set_fields(entry.url, kind, Path(entry.output_dir))
        return True

    # --- Telling the user ---

    def _notify_finished(self, title: str, body: str) -> None:
        """Tell the user, with a desktop notification, that the job ended while the window is not in front."""
        if self.is_active():
            return
        # GLib has no notification backend on Windows, so a Windows toast is used there.
        if winsupport.send_toast(title, body):
            return
        notification = Gio.Notification.new(title)
        notification.set_body(body)
        # Clicking the notification brings the window forward.
        notification.set_default_action("app.show-window")
        self.get_application().send_notification(_NOTIFICATION_ID, notification)

    def _open_output_folder(self) -> None:
        self._open_folder(str(self._form.output_dir))

    def _open_folder(self, folder: str) -> None:
        Gtk.FileLauncher.new(Gio.File.new_for_path(folder)).launch(self, None, None)

    def _on_close_request(self, _window: Gtk.Window) -> bool:
        if self._worker is not None:
            self._worker.cancel()
        return False

    # --- The Start / Stop button ---

    def _show_start_button(self) -> None:
        self._style_action_button("Start", add="suggested-action", remove="destructive-action")

    def _show_stop_button(self) -> None:
        self._style_action_button("Stop", add="destructive-action", remove="suggested-action")

    def _style_action_button(self, label: str, add: str, remove: str) -> None:
        self._action_button.set_label(label)
        self._action_button.set_sensitive(True)
        self._action_button.remove_css_class(remove)
        self._action_button.add_css_class(add)
        self._action_button.add_css_class("pill")
