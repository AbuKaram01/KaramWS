# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Finds article URLs: from a site's sitemap or feeds, or from a section's listing pages."""

from urllib.parse import urldefrag, urljoin, urlsplit

from trafilatura.feeds import find_feed_urls
from trafilatura.sitemaps import sitemap_search
from trafilatura.utils import load_html

from .classifier import is_homepage, looks_like_listing_path


def site_article_urls(site_url: str) -> list[str]:
    urls = sitemap_search(site_url) or find_feed_urls(site_url)
    return [url for url in urls if not is_homepage(url) and not looks_like_listing_path(url)]


def listing_page_url(section_url: str, page_number: int) -> str:
    """WordPress-style pagination: /section/page/2/, /section/page/3/, ..."""
    if page_number == 1:
        return section_url
    return f"{section_url.rstrip('/')}/page/{page_number}/"


def article_links(html: str, page_url: str) -> list[str]:
    """Links on a listing page that lead to articles, in page order, without duplicates."""
    tree = load_html(html)
    if tree is None:
        return []
    anchors = tree.xpath("//article//a[@href]") or tree.xpath("//h2//a[@href] | //h3//a[@href]")
    absolute = (urldefrag(urljoin(page_url, anchor.get("href"))).url for anchor in anchors)
    return list(dict.fromkeys(link for link in absolute if _is_article_link(link, page_url)))


def _is_article_link(link: str, page_url: str) -> bool:
    return (
        urlsplit(link).scheme in ("http", "https")
        and _site_of(link) == _site_of(page_url)
        and not is_homepage(link)
        and not looks_like_listing_path(link)
        and link.rstrip("/") != page_url.rstrip("/")
    )


def _site_of(url: str) -> str:
    return (urlsplit(url).hostname or "").removeprefix("www.")
