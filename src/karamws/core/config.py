# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Every tunable value in one place."""

from dataclasses import dataclass

from .. import __version__

CRAWLER_NAME = "KaramWS"


@dataclass(frozen=True)
class ScraperConfig:
    user_agent: str = f"Mozilla/5.0 (compatible; {CRAWLER_NAME}/{__version__})"
    request_delay_seconds: float = 1.0
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_delay_seconds: float = 2.0
    min_text_length: int = 200
    max_listing_pages: int = 200
    max_articles: int | None = None
    respect_robots: bool = True
    use_browser_fallback: bool = True
