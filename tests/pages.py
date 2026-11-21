# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""HTML snippets and a fake fetcher shared by the tests."""

from karamws.core.fetching import FetchError

PARAGRAPH = "فقرة طويلة نسبيا من مقال تجريبي عن الهواتف الذكية وكيفية اختيار الهاتف المناسب للاستخدام اليومي. " * 3


def article_page(title: str = "مراجعة هاتف تجريبي", head: str = "", extra_body: str = "") -> str:
    return f"""<html><head><title>{title}</title>{head}</head><body>
    <nav><ul><li><a href="/">Home</a></li></ul></nav>
    <article><h1>{title}</h1><p>{PARAGRAPH}</p>{extra_body}<p>{PARAGRAPH}</p></article>
    <footer>all rights reserved</footer></body></html>"""


def listing_page(paths: list[str]) -> str:
    cards = "".join(
        f'<article><h2><a href="{path}">post {path}</a></h2>'
        f'<a href="/category/news/">News</a><a href="{path}#comments">3 comments</a></article>'
        for path in paths
    )
    return f"<html><body>{cards}</body></html>"


class FakeFetcher:
    """Serves pages from a dict; anything else is a 404."""

    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.requested: list[str] = []
        self.closed = False

    def fetch(self, url: str) -> str:
        self.requested.append(url)
        if url not in self.pages:
            raise FetchError(f"HTTP 404 for {url}", status=404)
        return self.pages[url]

    def close(self) -> None:
        self.closed = True
