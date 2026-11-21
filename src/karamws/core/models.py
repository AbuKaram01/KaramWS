# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plain data types shared across the package."""

from dataclasses import dataclass
from enum import Enum


class UrlKind(Enum):
    ARTICLE = "article"
    SECTION = "section"
    SITE = "site"


class ScrapeStatus(Enum):
    SAVED = "saved"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class Article:
    url: str
    title: str
    text: str
    author: str | None = None
    published: str | None = None


@dataclass(frozen=True)
class ScrapeEvent:
    """One step of progress, meant to be shown to the user by a CLI or a GUI."""

    status: ScrapeStatus
    url: str
    detail: str = ""
