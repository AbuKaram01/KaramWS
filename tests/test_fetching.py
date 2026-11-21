# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

import time

import httpx
import pytest

from karamws.core.config import ScraperConfig
from karamws.core.fetching import FetchError, HttpFetcher, PoliteFetcher, RobotsChecker

from pages import FakeFetcher

URL = "https://site.com/page/"


def http_fetcher_answering(*responses: httpx.Response):
    calls: list[httpx.Request] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return queue.pop(0)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpFetcher(ScraperConfig(retry_delay_seconds=0), client=client), calls


def test_temporary_errors_are_retried():
    fetcher, calls = http_fetcher_answering(
        httpx.Response(503), httpx.Response(503), httpx.Response(200, text="ok")
    )
    assert fetcher.fetch(URL) == "ok"
    assert len(calls) == 3


def test_not_found_is_not_retried():
    fetcher, calls = http_fetcher_answering(httpx.Response(404))
    with pytest.raises(FetchError) as error:
        fetcher.fetch(URL)
    assert error.value.is_not_found
    assert len(calls) == 1


def polite(pages: dict[str, str], delay: float = 0.0) -> PoliteFetcher:
    robots = RobotsChecker(FakeFetcher(pages), "KaramWS")
    return PoliteFetcher(FakeFetcher(pages), delay, robots)


def test_urls_disallowed_by_robots_are_refused():
    pages = {
        "https://site.com/robots.txt": "User-agent: *\nDisallow: /private/",
        "https://site.com/private/x": "secret",
        "https://site.com/public/x": "fine",
    }
    fetcher = polite(pages)
    assert fetcher.fetch("https://site.com/public/x") == "fine"
    with pytest.raises(FetchError, match="robots.txt"):
        fetcher.fetch("https://site.com/private/x")


def test_missing_robots_txt_allows_everything():
    assert polite({"https://site.com/a": "fine"}).fetch("https://site.com/a") == "fine"


def test_requests_are_spaced_by_the_delay():
    pages = {"https://site.com/a": "a", "https://site.com/b": "b"}
    fetcher = polite(pages, delay=0.2)
    fetcher.fetch("https://site.com/a")
    started = time.monotonic()
    fetcher.fetch("https://site.com/b")
    assert time.monotonic() - started >= 0.15
