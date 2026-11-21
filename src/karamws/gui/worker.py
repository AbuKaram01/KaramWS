# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Runs a scrape on a background thread and reports back on the GTK main loop."""

import threading
from collections.abc import Callable

from ..core import ScrapeEvent, build_scraper

from .dispatch import run_on_main_thread
from .request import ScrapeRequest


class ScrapeWorker:
    """One scrape, one thread. The whole scrape stays on that thread, as the browser requires."""

    def __init__(
        self,
        request: ScrapeRequest,
        on_event: Callable[[ScrapeEvent], None],
        on_finished: Callable[[str | None], None],
    ):
        """Both callbacks run on the GTK main loop. `on_finished` gets an error message or None."""
        self._request = request
        self._on_event = on_event
        self._on_finished = on_finished
        self._cancelled = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        """Takes effect once the article being downloaded right now is done."""
        self._cancelled.set()

    def _run(self) -> None:
        error = None
        try:
            with build_scraper(self._request.output_dir, self._request.config) as scraper:
                for event in scraper.scrape(self._request.url, self._request.kind):
                    run_on_main_thread(self._on_event, event)
                    if self._cancelled.is_set():
                        break
        except Exception as unexpected:  # must reach the user instead of dying with the thread
            error = str(unexpected) or type(unexpected).__name__
        run_on_main_thread(self._on_finished, error)

