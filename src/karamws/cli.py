# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Command-line adapter. All scraping logic lives in the rest of the package."""

import argparse
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from . import __version__, winsupport
from .core import ScrapeEvent, ScrapeStatus, ScraperConfig, UrlKind, build_scraper

_AUTO = "auto"
_INTERRUPTED_EXIT_CODE = 130


def main(argv: Sequence[str] | None = None) -> int:
    winsupport.prepare_runtime()  # on Windows: console-less streams and the bundled Visual C++ runtime; else a no-op
    args = _parse_args(argv)
    config = ScraperConfig(
        request_delay_seconds=args.delay,
        max_articles=args.limit,
        respect_robots=not args.ignore_robots,
        use_browser_fallback=not args.no_browser,
    )
    kind = None if args.kind == _AUTO else UrlKind(args.kind)
    counts: Counter[ScrapeStatus] = Counter()
    try:
        with build_scraper(args.output, config) as scraper:
            for event in scraper.scrape(args.url, kind):
                counts[event.status] += 1
                print(_describe(event), flush=True)
    except KeyboardInterrupt:
        print("\nStopped.")
        return _INTERRUPTED_EXIT_CODE
    print(_summarize(counts))
    nothing_worked = counts[ScrapeStatus.FAILED] and not (
        counts[ScrapeStatus.SAVED] or counts[ScrapeStatus.SKIPPED]
    )
    return 1 if nothing_worked else 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="karamws",
        description="Save articles from a page, a section or a whole site as Markdown files.",
    )
    parser.add_argument("--version", action="version", version=f"KaramWS {__version__}")
    parser.add_argument("url", help="An article, a section/category page, or a site's home page")
    parser.add_argument("-o", "--output", type=Path, default=Path("output"),
                        help="Folder to save into (default: ./output)")
    parser.add_argument("--kind", choices=[_AUTO, *(kind.value for kind in UrlKind)],
                        default=_AUTO, help="What the URL points to (default: detect it)")
    parser.add_argument("--limit", type=int, help="Stop after this many articles")
    parser.add_argument("--delay", type=float, default=ScraperConfig.request_delay_seconds,
                        help="Seconds to wait between requests")
    parser.add_argument("--ignore-robots", action="store_true",
                        help="Do not obey robots.txt")
    parser.add_argument("--no-browser", action="store_true",
                        help="Never fall back to a real browser for JavaScript pages")
    return parser.parse_args(argv)


def _describe(event: ScrapeEvent) -> str:
    line = f"[{event.status.value}] {event.url}"
    return f"{line}  {event.detail}" if event.detail else line


def _summarize(counts: Counter[ScrapeStatus]) -> str:
    return (
        f"\nSaved {counts[ScrapeStatus.SAVED]}, "
        f"skipped {counts[ScrapeStatus.SKIPPED]}, "
        f"failed {counts[ScrapeStatus.FAILED]}."
    )
