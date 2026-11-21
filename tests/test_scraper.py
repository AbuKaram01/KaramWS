# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path

from karamws.core import scraper as scraper_module
from karamws.core.config import ScraperConfig
from karamws.core.extractor import ArticleExtractor
from karamws.core.models import ScrapeStatus, UrlKind
from karamws.core.scraper import Scraper
from karamws.core.storage import ArticleStore

from pages import FakeFetcher, article_page, listing_page

SAVED, SKIPPED, FAILED = ScrapeStatus.SAVED, ScrapeStatus.SKIPPED, ScrapeStatus.FAILED
JS_SHELL = "<html><body><div id='app'></div></body></html>"


def make_scraper(tmp_path, *fetchers, **config_overrides) -> Scraper:
    config = ScraperConfig(**config_overrides)
    extractor = ArticleExtractor(config.min_text_length)
    return Scraper(list(fetchers), extractor, ArticleStore(tmp_path), config)


def statuses(scraper: Scraper, url: str, kind: UrlKind | None = None) -> list[ScrapeStatus]:
    return [event.status for event in scraper.scrape(url, kind)]


def test_single_article_is_saved(tmp_path):
    url = "https://site.com/2026/post/"
    scraper = make_scraper(tmp_path, FakeFetcher({url: article_page()}))
    events = list(scraper.scrape(url))
    assert [event.status for event in events] == [SAVED]
    assert Path(events[0].detail).exists()


def test_already_saved_article_is_skipped_on_the_next_run(tmp_path):
    url = "https://site.com/2026/post/"
    scraper = make_scraper(tmp_path, FakeFetcher({url: article_page()}))
    assert statuses(scraper, url) == [SAVED]
    assert statuses(scraper, url) == [SKIPPED]


def test_browser_is_used_only_when_the_plain_page_has_no_article(tmp_path):
    url = "https://site.com/2026/post/"
    http, browser = FakeFetcher({url: JS_SHELL}), FakeFetcher({url: article_page()})
    scraper = make_scraper(tmp_path, http, browser)
    assert statuses(scraper, url, UrlKind.ARTICLE) == [SAVED]
    assert browser.requested == [url]


def test_unreadable_page_is_reported_not_raised(tmp_path):
    url = "https://site.com/2026/post/"
    scraper = make_scraper(tmp_path, FakeFetcher({url: JS_SHELL}))
    [event] = scraper.scrape(url, UrlKind.ARTICLE)
    assert event.status is FAILED and "No readable content" in event.detail


def section_pages() -> dict[str, str]:
    base = "https://site.com"
    pages = {
        f"{base}/category/news/": listing_page(["/a/", "/b/"]),
        f"{base}/category/news/page/2/": listing_page(["/c/"]),
    }
    pages.update({f"{base}/{name}/": article_page(name) for name in "abc"})
    return pages


def test_section_is_detected_and_followed_until_a_page_is_missing(tmp_path):
    scraper = make_scraper(tmp_path, FakeFetcher(section_pages()))
    assert statuses(scraper, "https://site.com/category/news/") == [SAVED, SAVED, SAVED]


def test_section_stops_when_a_page_repeats_the_same_links(tmp_path):
    pages = section_pages()
    pages["https://site.com/category/news/page/2/"] = pages["https://site.com/category/news/"]
    scraper = make_scraper(tmp_path, FakeFetcher(pages))
    assert statuses(scraper, "https://site.com/category/news/") == [SAVED, SAVED]


def test_max_articles_limits_the_run(tmp_path):
    scraper = make_scraper(tmp_path, FakeFetcher(section_pages()), max_articles=2)
    assert statuses(scraper, "https://site.com/category/news/") == [SAVED, SAVED]


def test_missing_first_listing_page_is_reported(tmp_path):
    scraper = make_scraper(tmp_path, FakeFetcher({}))
    assert statuses(scraper, "https://site.com/category/none/", UrlKind.SECTION) == [FAILED]


def test_whole_site_uses_the_sitemap_urls(tmp_path, monkeypatch):
    post = "https://site.com/2026/post/"
    monkeypatch.setattr(scraper_module, "site_article_urls", lambda url: [post])
    scraper = make_scraper(tmp_path, FakeFetcher({post: article_page()}))
    assert statuses(scraper, "https://site.com/") == [SAVED]


def test_site_without_sitemap_or_feed_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(scraper_module, "site_article_urls", lambda url: [])
    [event] = make_scraper(tmp_path, FakeFetcher({})).scrape("https://site.com/")
    assert event.status is FAILED and "No sitemap or feed" in event.detail


def test_leaving_the_context_closes_every_fetcher(tmp_path):
    fetchers = [FakeFetcher({}), FakeFetcher({})]
    with make_scraper(tmp_path, *fetchers):
        pass
    assert all(fetcher.closed for fetcher in fetchers)
