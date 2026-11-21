# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""What the user asked for, independent of any widget."""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from ..core import ScraperConfig, UrlKind


@dataclass(frozen=True)
class ScrapeRequest:
    url: str
    kind: UrlKind | None
    output_dir: Path
    config: ScraperConfig


def normalize_url(text: str) -> str | None:
    """Accept what people actually type: 'example.com/post' becomes 'https://example.com/post'."""
    text = text.strip()
    if not text or " " in text:
        return None
    if "://" not in text:
        text = f"https://{text}"
    parts = urlsplit(text)
    return text if parts.scheme in ("http", "https") and parts.netloc else None
