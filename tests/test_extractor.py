# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

from karamws.core.extractor import ArticleExtractor

from pages import article_page

URL = "https://site.com/post/"


def test_keeps_the_article_and_drops_page_chrome():
    article = ArticleExtractor(min_text_length=100).extract(article_page(), URL)
    assert article.title == "مراجعة هاتف تجريبي"
    assert "الهواتف الذكية" in article.text
    assert "all rights reserved" not in article.text


def test_table_cells_are_kept():
    table = "<table><tr><td>الشاشة</td><td>6.5 بوصة</td></tr></table>"
    article = ArticleExtractor(min_text_length=100).extract(article_page(extra_body=table), URL)
    assert "الشاشة" in article.text and "6.5" in article.text


def test_page_with_too_little_text_is_not_an_article():
    html = "<html><body><p>hi</p></body></html>"
    assert ArticleExtractor(min_text_length=100).extract(html, URL) is None


def test_text_does_not_repeat_the_title():
    article = ArticleExtractor(min_text_length=100).extract(article_page(), URL)
    assert not article.text.startswith(article.title)
