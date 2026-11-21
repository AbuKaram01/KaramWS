# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The scraping engine: no GUI and no printing, so a command line, a window or a test can all drive it."""

from .config import ScraperConfig
from .models import Article, ScrapeEvent, ScrapeStatus, UrlKind
from .scraper import Scraper, build_scraper

__all__ = [
    "Article",
    "ScrapeEvent",
    "ScrapeStatus",
    "Scraper",
    "ScraperConfig",
    "UrlKind",
    "build_scraper",
]
