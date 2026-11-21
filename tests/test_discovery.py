# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

from karamws.core import discovery
from karamws.core.discovery import article_links, listing_page_url, site_article_urls

from pages import listing_page


def test_article_links_skip_categories_and_fragment_duplicates():
    html = listing_page(["/2026/a/", "/2026/b/"])
    assert article_links(html, "https://site.com/news/") == [
        "https://site.com/2026/a/",
        "https://site.com/2026/b/",
    ]


def test_without_article_elements_headings_are_used_and_other_sites_ignored():
    html = (
        '<h2><a href="/a/">A</a></h2>'
        '<h2><a href="https://other.com/b/">B</a></h2>'
        '<h3><a href="https://www.site.com/c/">C</a></h3>'
    )
    assert article_links(html, "https://site.com/news/") == [
        "https://site.com/a/",
        "https://www.site.com/c/",
    ]


def test_listing_page_urls_follow_the_page_number_pattern():
    section = "https://site.com/category/news/"
    assert listing_page_url(section, 1) == section
    assert listing_page_url(section, 3) == "https://site.com/category/news/page/3/"


def test_site_urls_drop_the_homepage_and_listing_pages(monkeypatch):
    monkeypatch.setattr(
        discovery,
        "sitemap_search",
        lambda url: ["https://site.com/", "https://site.com/category/x/", "https://site.com/post/"],
    )
    assert site_article_urls("https://site.com/") == ["https://site.com/post/"]


def test_feeds_are_used_when_there_is_no_sitemap(monkeypatch):
    monkeypatch.setattr(discovery, "sitemap_search", lambda url: [])
    monkeypatch.setattr(discovery, "find_feed_urls", lambda url: ["https://site.com/from-feed/"])
    assert site_article_urls("https://site.com/") == ["https://site.com/from-feed/"]
