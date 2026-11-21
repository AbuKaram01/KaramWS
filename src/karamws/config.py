# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The settings the user can change (Preferences), saved in a small JSON file in the user's config directory.

Not to be mixed up with ``karamws.core.config.ScraperConfig``: that is what the engine is told for one run, and
``AppConfig.scraper_config()`` makes it from these saved settings.
"""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .core.config import ScraperConfig
from .core.paths import config_dir

DEFAULT_HISTORY_LIMIT = 200
MIN_HISTORY_LIMIT = 10
MAX_HISTORY_LIMIT = 10_000


def config_file() -> Path:
    return config_dir() / "config.json"


@dataclass
class AppConfig:
    """The user's saved settings, as one flat record serialised to ``config.json``.

    Use ``load()`` to read the file and ``save()`` to write it. To change a few settings from a window, prefer
    ``update_saved_config()``, which re-reads the file first so that edits made elsewhere are not lost.
    """

    # Where the articles are saved; empty = the default folder (Documents/Articles), chosen by the interface.
    output_dir: str = ""
    # Stop after this many articles; 0 = no limit.
    max_articles: int = 0
    request_delay_seconds: float = 1.0
    respect_robots: bool = True
    use_browser_fallback: bool = True
    # A desktop notification when a job ends while the window is not in front. On by default: a long job is the very
    # case where nobody is watching the window.
    notify_when_done: bool = True
    # Keep a list of the jobs that ended (Menu > History), up to this many.
    history_enabled: bool = True
    history_limit: int = DEFAULT_HISTORY_LIMIT
    # Set once the first-run welcome guide has been shown, so it never reappears by itself.
    welcome_done: bool = False

    @property
    def history_keep(self) -> int:
        """How many jobs to keep: the saved limit, clamped to the allowed range.

        Clamping means that a hand-edited file cannot make the history delete everything.
        """
        return min(max(self.history_limit, MIN_HISTORY_LIMIT), MAX_HISTORY_LIMIT)

    def scraper_config(self) -> ScraperConfig:
        """What the engine is told for a run, from these settings."""
        return ScraperConfig(
            request_delay_seconds=max(self.request_delay_seconds, 0.0),
            max_articles=self.max_articles if self.max_articles > 0 else None,
            respect_robots=self.respect_robots,
            use_browser_fallback=self.use_browser_fallback,
        )

    @classmethod
    def load(cls) -> "AppConfig":
        """Return the saved settings.

        Never raises and never returns a value of the wrong type. A missing or unreadable file gives the defaults; a
        file whose content is not a JSON object is also set aside as ``config.json.broken`` rather than silently
        overwritten. Any single field holding the wrong kind of value (in a hand-edited file) falls back to its
        default instead of crashing whatever window reads it next.
        """
        defaults = asdict(cls())
        path = config_file()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return cls()
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("not a JSON object")
        except ValueError:
            try:
                os.replace(path, path.with_name(path.name + ".broken"))
            except OSError:
                pass
            return cls()
        for key, value in data.items():
            if key in defaults and _same_kind(value, defaults[key]):
                defaults[key] = float(value) if isinstance(defaults[key], float) else value
        return cls(**defaults)

    def save(self) -> None:
        """Write the settings to disk atomically: a crash mid-save never leaves a half-written file."""
        path = config_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)


def update_saved_config(**changes) -> AppConfig:
    """Change some settings in the file *as it is now* and save it. A name that is not a setting is a bug."""
    config = AppConfig.load()
    for name, value in changes.items():
        if not hasattr(config, name):
            raise AttributeError(f"{name!r} is not a setting")
        setattr(config, name, value)
    config.save()
    return config


def _same_kind(value, default) -> bool:
    """Whether ``value`` may replace a field whose default is ``default`` (bool is checked first: it is an int)."""
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(default, float):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value  # not NaN
    if isinstance(default, str):
        return isinstance(value, str)
    return True
