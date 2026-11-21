# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

from karamws.core.classifier import classify_page, is_homepage
from karamws.core.models import UrlKind

from pages import article_page, listing_page


def test_only_a_bare_root_is_a_homepage():
    assert is_homepage("https://site.com/")
    assert not is_homepage("https://site.com/?p=12")
    assert not is_homepage("https://site.com/news/")


def test_plain_page_is_an_article():
    assert classify_page("https://site.com/2026/post/", article_page()) is UrlKind.ARTICLE


def test_category_path_is_a_section():
    assert classify_page("https://site.com/category/news/", "<html></html>") is UrlKind.SECTION


def test_page_full_of_article_cards_is_a_section():
    html = listing_page(["/a/", "/b/", "/c/", "/d/"])
    assert classify_page("https://site.com/news/", html) is UrlKind.SECTION


def test_declared_article_wins_over_a_listing_looking_path():
    head = '<meta property="og:type" content="article">'
    assert classify_page("https://site.com/tag/x/post/", article_page(head=head)) is UrlKind.ARTICLE
