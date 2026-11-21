# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Ties discovery, fetching, extraction and storage together.

Nothing here prints or reads input: scrape() yields ScrapeEvent objects, so a
command line, a GUI or a test can all drive it the same way.
"""

import itertools
from collections.abc import Callable, Iterator, Sequence
from functools import partial
from pathlib import Path
from typing import TypeVar

from .classifier import classify_page, is_homepage
from .config import CRAWLER_NAME, ScraperConfig
from .discovery import article_links, listing_page_url, site_article_urls
from .extractor import ArticleExtractor
from .fetching import (
    BrowserFetcher,
    Fetcher,
    FetchError,
    HttpFetcher,
    PoliteFetcher,
    RobotsChecker,
)
from .models import ScrapeEvent, ScrapeStatus, UrlKind
from .storage import ArticleStore

Parsed = TypeVar("Parsed")


class Scraper:
    def __init__(
        self,
        fetchers: Sequence[Fetcher],
        extractor: ArticleExtractor,
        store: ArticleStore,
        config: ScraperConfig,
    ):
        """`fetchers` are tried in order: the cheap one first, the browser last."""
        self._fetchers = fetchers
        self._extractor = extractor
        self._store = store
        self._config = config

    def __enter__(self) -> "Scraper":
        return self

    def __exit__(self, *exc_info) -> None:
        for fetcher in self._fetchers:
            fetcher.close()

    def scrape(self, url: str, kind: UrlKind | None = None) -> Iterator[ScrapeEvent]:
        """Yield one event per article. Stop iterating to cancel."""
        try:
            kind = kind or self._detect_kind(url)
            article_urls = itertools.islice(
                self._discover(url, kind), self._config.max_articles
            )
            for article_url in article_urls:
                yield self._scrape_article(article_url)
        except FetchError as error:
            yield ScrapeEvent(ScrapeStatus.FAILED, url, str(error))

    def _detect_kind(self, url: str) -> UrlKind:
        if is_homepage(url):
            return UrlKind.SITE
        html = self._fetch_and_parse(url, lambda page: page)
        return classify_page(url, html)

    def _discover(self, url: str, kind: UrlKind) -> Iterator[str]:
        if kind is UrlKind.ARTICLE:
            yield url
        elif kind is UrlKind.SECTION:
            yield from self._discover_section(url)
        else:
            yield from self._discover_site(url)

    def _discover_site(self, site_url: str) -> Iterator[str]:
        urls = site_article_urls(site_url)
        if not urls:
            raise FetchError(
                f"No sitemap or feed found for {site_url}. Try the URL of a section instead."
            )
        yield from urls

    def _discover_section(self, section_url: str) -> Iterator[str]:
        seen: set[str] = set()
        for page_number in range(1, self._config.max_listing_pages + 1):
            page_url = listing_page_url(section_url, page_number)
            try:
                links = self._fetch_and_parse(
                    page_url, partial(article_links, page_url=page_url)
                )
            except FetchError:
                if page_number == 1:
                    raise
                return  # ran past the last page
            new_links = [link for link in links if link not in seen]
            if not new_links:
                return
            seen.update(new_links)
            yield from new_links

    def _scrape_article(self, url: str) -> ScrapeEvent:
        if self._store.contains(url):
            return ScrapeEvent(ScrapeStatus.SKIPPED, url, "already saved")
        try:
            article = self._fetch_and_parse(
                url, partial(self._extractor.extract, url=url)
            )
        except FetchError as error:
            return ScrapeEvent(ScrapeStatus.FAILED, url, str(error))
        return ScrapeEvent(ScrapeStatus.SAVED, url, str(self._store.save(article)))

    def _fetch_and_parse(
        self, url: str, parse: Callable[[str], Parsed | None]
    ) -> Parsed:
        """Fetch with each fetcher in turn until `parse` finds something in the page."""
        last_error = FetchError(f"No readable content at {url}")
        for fetcher in self._fetchers:
            try:
                parsed = parse(fetcher.fetch(url))
            except FetchError as error:
                if error.is_not_found:
                    raise
                last_error = error
                continue
            if parsed:
                return parsed
        raise last_error


def build_scraper(output_dir: Path, config: ScraperConfig = ScraperConfig()) -> Scraper:
    """Wire up the default components. Use as `with build_scraper(...) as scraper:`."""
    http = HttpFetcher(config)
    robots = RobotsChecker(http, CRAWLER_NAME) if config.respect_robots else None
    fetchers: list[Fetcher] = [PoliteFetcher(http, config.request_delay_seconds, robots)]
    if config.use_browser_fallback:
        fetchers.append(BrowserFetcher(config))
    return Scraper(
        fetchers, ArticleExtractor(config.min_text_length), ArticleStore(output_dir), config
    )
