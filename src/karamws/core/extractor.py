# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Turns a page's HTML into an Article, keeping the main text and dropping menus, ads and footers."""

import json

import trafilatura

from .models import Article


class ArticleExtractor:
    def __init__(self, min_text_length: int):
        self._min_text_length = min_text_length

    def extract(self, html: str, url: str) -> Article | None:
        """Return the article, or None when the page has no readable article text."""
        raw = trafilatura.extract(
            html,
            url=url,
            output_format="json",
            with_metadata=True,
            include_tables=True,
        )
        if raw is None:
            return None
        fields = json.loads(raw)
        text = fields.get("text") or ""
        if len(text) < self._min_text_length:
            return None
        title = fields.get("title") or url
        return Article(
            url=url,
            title=title,
            text=_without_leading_title(text, title),
            author=fields.get("author"),
            published=fields.get("date"),
        )


def _without_leading_title(text: str, title: str) -> str:
    """The saved file already starts with the title, so drop it if the text repeats it."""
    first_line, _, rest = text.partition("\n")
    return rest.lstrip() if first_line.strip() == title.strip() else text
