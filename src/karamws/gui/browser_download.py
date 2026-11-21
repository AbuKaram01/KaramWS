# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Downloading the Chromium that Playwright drives, and the row that shows and controls it.

The download belongs to the application (``BrowserDownloads``), not to the window that started it, so closing
Preferences or the welcome guide does not interrupt it. The row is shared by both of them.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from gi.repository import Adw, Gtk

from ..core.browser import (
    BrowserInstallCancelled,
    BrowserInstallError,
    ChromiumInstaller,
    chromium_ready,
    percent_in,
)
from .dispatch import run_on_main_thread

_DOWNLOAD_SIZE_HINT = "about 150 MB"


class BrowserEventKind(Enum):
    STARTED = "started"
    PROGRESS = "progress"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True)
class BrowserEvent:
    kind: BrowserEventKind
    percent: int | None = None
    message: str = ""


class BrowserDownloads:
    """One Chromium download at a time, reported to whoever subscribed. Events arrive on the GTK main loop."""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[BrowserEvent], None]] = []
        self._installer: ChromiumInstaller | None = None

    @property
    def running(self) -> bool:
        return self._installer is not None

    def subscribe(self, callback: Callable[[BrowserEvent], None]) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[BrowserEvent], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def start(self) -> None:
        """Begin the download (nothing happens while one is already running)."""
        if self._installer is not None:
            return
        self._installer = ChromiumInstaller()
        self._publish(BrowserEvent(BrowserEventKind.STARTED))
        threading.Thread(target=self._run, args=(self._installer,), daemon=True).start()

    def stop(self) -> None:
        if self._installer is not None:
            self._installer.cancel()

    def _run(self, installer: ChromiumInstaller) -> None:
        def on_line(line: str) -> None:
            self._post(BrowserEvent(BrowserEventKind.PROGRESS, percent_in(line), line))

        try:
            installer.run(on_line)
            ended = BrowserEvent(BrowserEventKind.FINISHED)
        except BrowserInstallCancelled:
            ended = BrowserEvent(BrowserEventKind.CANCELLED)
        except BrowserInstallError as error:
            ended = BrowserEvent(BrowserEventKind.FAILED, message=str(error))
        except OSError as error:  # the program could not even start (no Python, no permission)
            ended = BrowserEvent(BrowserEventKind.FAILED, message=str(error))
        self._post(ended)

    def _post(self, event: BrowserEvent) -> None:
        run_on_main_thread(self._publish, event)

    def _publish(self, event: BrowserEvent) -> None:
        if event.kind in (BrowserEventKind.FINISHED, BrowserEventKind.CANCELLED, BrowserEventKind.FAILED):
            self._installer = None
        for callback in list(self._subscribers):
            callback(event)


class BrowserRow(Adw.ActionRow):
    """Shows whether Chromium is there, and downloads it (or stops the download) with one button."""

    def __init__(self, downloads: BrowserDownloads, on_message: Callable[[str], None]) -> None:
        super().__init__(title="Chromium", use_markup=False, subtitle_lines=0)
        self._downloads = downloads
        self._on_message = on_message
        self._percent: int | None = None

        self._icon = Gtk.Image(icon_name="object-select-symbolic")
        self.add_prefix(self._icon)
        self._progress = Gtk.ProgressBar(valign=Gtk.Align.CENTER, width_request=90, visible=False)
        self._button = Gtk.Button(valign=Gtk.Align.CENTER)
        self._button.connect("clicked", self._on_button_clicked)
        self.add_suffix(self._progress)
        self.add_suffix(self._button)

        downloads.subscribe(self._on_event)
        self.refresh()

    def detach(self) -> None:
        """Stop following the download (the owner calls this when it closes)."""
        self._downloads.unsubscribe(self._on_event)

    def refresh(self) -> None:
        """Show the state as it is now: ready, missing, or downloading."""
        running = self._downloads.running
        ready = chromium_ready()
        self._progress.set_visible(running)
        if running:
            self._show_running()
        elif ready:
            self._show("object-select-symbolic", "Ready. Pages that need JavaScript can be read.", None)
        else:
            self._show(
                "folder-download-symbolic",
                f"Not installed. Needed only for pages that need JavaScript ({_DOWNLOAD_SIZE_HINT}, downloaded once).",
                "Download",
            )

    def _show_running(self) -> None:
        text = "Downloading…" if self._percent is None else f"Downloading… {self._percent}%"
        self._show("folder-download-symbolic", text, "Stop")
        if self._percent is None:
            self._progress.pulse()
        else:
            self._progress.set_fraction(self._percent / 100)

    def _show(self, icon_name: str, subtitle: str, button_label: str | None) -> None:
        self._icon.set_from_icon_name(icon_name)
        self.set_subtitle(subtitle)
        self._button.set_visible(button_label is not None)
        if button_label is not None:
            self._button.set_label(button_label)
            stopping = button_label == "Stop"
            self._button.add_css_class("destructive-action" if stopping else "suggested-action")
            self._button.remove_css_class("suggested-action" if stopping else "destructive-action")

    def _on_button_clicked(self, _button: Gtk.Button) -> None:
        if self._downloads.running:
            self._downloads.stop()
        else:
            self._percent = None
            self._downloads.start()

    def _on_event(self, event: BrowserEvent) -> None:
        if event.kind is BrowserEventKind.PROGRESS:
            if event.percent is not None:
                self._percent = event.percent
        elif event.kind is BrowserEventKind.FINISHED:
            self._on_message("Chromium downloaded.")
        elif event.kind is BrowserEventKind.CANCELLED:
            self._on_message("Download stopped. Press Download to try again.")
        elif event.kind is BrowserEventKind.FAILED:
            self._on_message(f"Download failed: {event.message}")
        self.refresh()
