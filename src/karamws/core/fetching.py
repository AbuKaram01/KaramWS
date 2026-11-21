# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Everything that touches the network: plain HTTP, a real browser, and politeness rules."""

import os
import time
from typing import Protocol
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from .config import ScraperConfig
from .browser import chromium_home
from .paths import BROWSERS_ENV

_NOT_FOUND_STATUSES = {404, 410}
_TOO_MANY_REQUESTS = 429
_FIRST_SERVER_ERROR = 500
_BROWSER_BLOCKED_RESOURCES = {"image", "media", "font"}
_BROWSER_RENDER_WAIT_MS = 1000


class FetchError(Exception):
    """A page could not be obtained, or had nothing usable in it."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status

    @property
    def is_not_found(self) -> bool:
        return self.status in _NOT_FOUND_STATUSES

    @property
    def is_transient(self) -> bool:
        """Worth retrying: no response at all, rate limiting, or a server-side error."""
        return (
            self.status is None
            or self.status == _TOO_MANY_REQUESTS
            or self.status >= _FIRST_SERVER_ERROR
        )


class Fetcher(Protocol):
    def fetch(self, url: str) -> str: ...

    def close(self) -> None: ...


class HttpFetcher:
    """Fast path: a plain HTTP request, retried when the failure looks temporary."""

    def __init__(self, config: ScraperConfig, client: httpx.Client | None = None):
        self._config = config
        self._client = client or httpx.Client(
            headers={"User-Agent": config.user_agent},
            timeout=config.timeout_seconds,
            follow_redirects=True,
        )

    def fetch(self, url: str) -> str:
        retries_left = self._config.max_retries
        while True:
            try:
                return self._get(url)
            except FetchError as error:
                if not error.is_transient or retries_left == 0:
                    raise
                retries_left -= 1
                time.sleep(self._config.retry_delay_seconds)

    def close(self) -> None:
        self._client.close()

    def _get(self, url: str) -> str:
        try:
            response = self._client.get(url)
        except (httpx.HTTPError, httpx.InvalidURL) as error:
            raise FetchError(f"Could not reach {url}: {error}") from error
        if response.status_code >= 400:
            raise FetchError(
                f"HTTP {response.status_code} for {url}", status=response.status_code
            )
        return response.text


class RobotsChecker:
    """Answers "may I fetch this URL?" from each site's robots.txt (cached per site).

    A missing or unreachable robots.txt means everything is allowed.
    """

    def __init__(self, fetcher: Fetcher, agent_name: str):
        self._fetcher = fetcher
        self._agent_name = agent_name
        self._parsers: dict[str, RobotFileParser] = {}

    def allows(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._parsers:
            self._parsers[origin] = self._load(origin)
        return self._parsers[origin].can_fetch(self._agent_name, url)

    def _load(self, origin: str) -> RobotFileParser:
        parser = RobotFileParser()
        try:
            parser.parse(self._fetcher.fetch(f"{origin}/robots.txt").splitlines())
        except FetchError:
            parser.parse([])
        return parser


class PoliteFetcher:
    """Wraps another fetcher with a pause between requests and robots.txt rules."""

    def __init__(
        self, inner: Fetcher, delay_seconds: float, robots: RobotsChecker | None = None
    ):
        self._inner = inner
        self._delay_seconds = delay_seconds
        self._robots = robots
        self._last_request_at: float | None = None

    def fetch(self, url: str) -> str:
        if self._robots is not None and not self._robots.allows(url):
            raise FetchError(f"robots.txt does not allow fetching {url}")
        self._wait_for_turn()
        try:
            return self._inner.fetch(url)
        finally:
            self._last_request_at = time.monotonic()

    def close(self) -> None:
        self._inner.close()

    def _wait_for_turn(self) -> None:
        if self._last_request_at is None:
            return
        remaining = self._delay_seconds - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)


class BrowserFetcher:
    """Slow path: loads pages in a real Chromium so JavaScript-rendered content is included.

    Playwright's sync API belongs to the thread that started it, so keep every
    call to one instance on a single thread (a GUI should run the whole scrape
    inside one worker thread).
    """

    def __init__(self, config: ScraperConfig):
        self._config = config
        self._api = None
        self._playwright = None
        self._browser = None
        self._page = None

    def fetch(self, url: str) -> str:
        page = self._ensure_page()
        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self._config.timeout_seconds * 1000,
            )
            if response is not None and response.status >= 400:
                raise FetchError(f"HTTP {response.status} for {url}", status=response.status)
            page.wait_for_timeout(_BROWSER_RENDER_WAIT_MS)
            return page.content()
        except self._api.Error as error:
            raise FetchError(f"Browser could not load {url}: {error}") from error

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._page = self._browser = self._playwright = None

    def _ensure_page(self):
        if self._page is None:
            self._page = self._start()
        return self._page

    def _start(self):
        self._api = _load_playwright()
        _use_bundled_browsers()
        try:
            self._playwright = self._api.sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
        except self._api.Error as error:
            self.close()
            raise FetchError(
                f"Could not start the browser (run `playwright install chromium`): {error}"
            ) from error
        context = self._browser.new_context(user_agent=self._config.user_agent)
        context.route("**/*", _block_heavy_resources)
        return context.new_page()


def _use_bundled_browsers() -> None:
    """Point Playwright at the Chromium of the installation (or the one the user downloaded). A setting wins."""
    folder = chromium_home()
    if folder is not None:
        os.environ.setdefault(BROWSERS_ENV, str(folder))


def _load_playwright():
    try:
        from playwright import sync_api
    except ImportError as error:
        raise FetchError(
            "This page needs a real browser, but Playwright is not installed "
            "(pip install playwright && playwright install chromium)."
        ) from error
    return sync_api


def _block_heavy_resources(route) -> None:
    if route.request.resource_type in _BROWSER_BLOCKED_RESOURCES:
        route.abort()
    else:
        route.continue_()
