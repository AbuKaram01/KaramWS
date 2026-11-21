# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Decides what a URL points to: one article, a section listing, or a whole site."""

from urllib.parse import urlsplit

from trafilatura import extract_metadata
from trafilatura.utils import load_html

from .models import UrlKind

_LISTING_PATH_SEGMENTS = frozenset(
    {"category", "categories", "tag", "tags", "topic", "topics",
     "section", "author", "archive", "page"}
)
_MIN_ARTICLE_ELEMENTS_IN_LISTING = 3


def is_homepage(url: str) -> bool:
    parts = urlsplit(url)
    return not parts.path.strip("/") and not parts.query


def looks_like_listing_path(url: str) -> bool:
    segments = urlsplit(url).path.lower().split("/")
    return any(segment in _LISTING_PATH_SEGMENTS for segment in segments)


def classify_page(url: str, html: str) -> UrlKind:
    """Tell an ARTICLE from a SECTION. Homepages are recognised by is_homepage() instead."""
    if _declares_article(html):
        return UrlKind.ARTICLE
    if looks_like_listing_path(url) or _has_many_article_elements(html):
        return UrlKind.SECTION
    return UrlKind.ARTICLE


def _declares_article(html: str) -> bool:
    metadata = extract_metadata(html)
    return metadata is not None and metadata.pagetype == "article"


def _has_many_article_elements(html: str) -> bool:
    tree = load_html(html)
    return tree is not None and len(tree.xpath("//article")) >= _MIN_ARTICLE_ELEMENTS_IN_LISTING
