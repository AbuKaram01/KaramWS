# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Saves articles as Markdown files: <output>/<site>/<title-slug>-<url-hash>.md"""

import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit

from .models import Article

_MAX_SLUG_LENGTH = 60
_URL_DIGEST_LENGTH = 10
_FALLBACK_SLUG = "article"
_FALLBACK_SITE = "unknown-site"


class ArticleStore:
    def __init__(self, root: Path):
        self._root = Path(root)

    def contains(self, url: str) -> bool:
        pattern = f"*-{_url_digest(url)}.md"
        return any(self._site_folder(url).glob(pattern))

    def save(self, article: Article) -> Path:
        folder = self._site_folder(article.url)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{_slugify(article.title)}-{_url_digest(article.url)}.md"
        path.write_text(_render(article), encoding="utf-8")
        return path

    def _site_folder(self, url: str) -> Path:
        return self._root / (urlsplit(url).hostname or _FALLBACK_SITE)


def _slugify(title: str) -> str:
    """Keep letters of any language (Arabic included), digits and dashes."""
    words = re.sub(r"[^\w\s-]", "", title).split()
    return "-".join(words)[:_MAX_SLUG_LENGTH].strip("-") or _FALLBACK_SLUG


def _url_digest(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:_URL_DIGEST_LENGTH]


def _render(article: Article) -> str:
    details = [
        ("Source", article.url),
        ("Author", article.author),
        ("Published", article.published),
    ]
    detail_lines = [f"- {label}: {value}" for label, value in details if value]
    return "\n".join([f"# {article.title}", "", *detail_lines, "", article.text, ""])
