# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The Chromium that Playwright drives: where it is, whether it is there, and downloading it.

The installers carry a Chromium (``browsers`` beside the virtual environment). When one is missing (an installation
made with ``-NoBrowsers``, or a Linux package whose download failed) the program can fetch one itself: into the
installation's ``browsers`` folder when that can be written, else into the user's own data folder.
"""

import os
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from .paths import BROWSERS_ENV, bundled_browsers_dir, install_dir, is_windows, user_browsers_dir

# The folder Playwright launches headless Chromium from (a full Chromium is downloaded beside it).
_CHROMIUM_FOLDER_PREFIX = "chromium_headless_shell-"
PLAYWRIGHT_COMMAND = (sys.executable, "-m", "playwright")
_PERCENT = re.compile(r"(\d{1,3})\s*%")
_LOG_LINES_IN_ERROR = 6


class BrowserInstallError(Exception):
    """The download did not give a usable Chromium."""


class BrowserInstallCancelled(Exception):
    """The user stopped the download."""


def has_chromium(folder: Path | None) -> bool:
    """Whether ``folder`` holds the Chromium that Playwright launches."""
    if folder is None or not folder.is_dir():
        return False
    return any(folder.glob(f"{_CHROMIUM_FOLDER_PREFIX}*"))


def chromium_home() -> Path | None:
    """The browsers folder of this installation that holds a Chromium: beside the environment, else the user's own."""
    for folder in (bundled_browsers_dir(), user_browsers_dir()):
        if has_chromium(folder):
            return folder
    return None


def _playwright_default_dir() -> Path:
    if is_windows():
        local = os.environ.get("LOCALAPPDATA")
        return (Path(local) if local else Path.home() / "AppData" / "Local") / "ms-playwright"
    cache = os.environ.get("XDG_CACHE_HOME")
    return (Path(cache) if cache else Path.home() / ".cache") / "ms-playwright"


def chromium_ready() -> bool:
    """Whether a Chromium is available to the program: its own, or the one Playwright would use by itself."""
    if chromium_home() is not None:
        return True
    explicit = os.environ.get(BROWSERS_ENV)
    return has_chromium(Path(explicit) if explicit else _playwright_default_dir())


def install_target() -> Path:
    """Where a download goes: beside the environment when that can be written, else the user's data folder."""
    beside = install_dir() / "browsers"
    can_write = os.access(beside if beside.exists() else install_dir(), os.W_OK)
    return beside if can_write else user_browsers_dir()


def percent_in(line: str) -> int | None:
    """The progress Playwright prints in a line of its output (``|■■■■    |  40% of 150.2 MiB``), if there is one."""
    found = _PERCENT.search(line)
    if found is None:
        return None
    return min(int(found.group(1)), 100)


class ChromiumInstaller:
    """Runs ``playwright install chromium`` into a target folder, reporting its output line by line."""

    def __init__(self, target: Path | None = None, command: Sequence[str] = PLAYWRIGHT_COMMAND):
        self._target = target or install_target()
        self._command = [*command, "install", "chromium"]
        self._process: subprocess.Popen | None = None
        self._cancelled = False

    @property
    def target(self) -> Path:
        return self._target

    def run(self, on_line: Callable[[str], None]) -> None:
        """Download Chromium. Blocks until it ends; raises BrowserInstallError or BrowserInstallCancelled."""
        self._target.mkdir(parents=True, exist_ok=True)
        environment = {**os.environ, BROWSERS_ENV: str(self._target)}
        # A program without a console (the Windows Start menu entry) must not flash a console window for the download.
        flags = subprocess.CREATE_NO_WINDOW if is_windows() else 0
        self._process = subprocess.Popen(
            self._command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
            env=environment, creationflags=flags,
        )
        tail: list[str] = []
        for line in self._process.stdout:
            line = line.strip()
            if line:
                tail = [*tail, line][-_LOG_LINES_IN_ERROR:]
                on_line(line)
        exit_code = self._process.wait()
        if self._cancelled:
            raise BrowserInstallCancelled
        if exit_code != 0 or not has_chromium(self._target):
            raise BrowserInstallError("; ".join(tail) or f"the download ended with exit code {exit_code}")

    def cancel(self) -> None:
        """Stop the download (safe to call from another thread, and when nothing is running)."""
        self._cancelled = True
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
