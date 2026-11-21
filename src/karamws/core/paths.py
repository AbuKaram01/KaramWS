# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Per-user and per-installation filesystem locations, for Linux and Windows.

Linux follows the XDG Base Directory specification. Windows uses ``%LOCALAPPDATA%``. On either system an explicit
``XDG_DATA_HOME`` wins, which also makes a portable setup possible.
"""

import os
import sys
from pathlib import Path

APP_NAME = "karamws"

# The environment variable Playwright reads to know where its browsers are.
BROWSERS_ENV = "PLAYWRIGHT_BROWSERS_PATH"
_BROWSERS_FOLDER = "browsers"


def is_windows() -> bool:
    return sys.platform == "win32"


def config_dir() -> Path:
    """The per-user configuration directory (``config.json``)."""
    explicit = os.environ.get("XDG_CONFIG_HOME")
    if explicit:
        return Path(explicit) / APP_NAME
    if is_windows():
        roaming = os.environ.get("APPDATA")
        return (Path(roaming) if roaming else Path.home() / "AppData" / "Roaming") / APP_NAME
    return Path.home() / ".config" / APP_NAME


def data_dir() -> Path:
    """The per-user data directory (the log file, the history, a GTK runtime or Chromium that was downloaded)."""
    explicit = os.environ.get("XDG_DATA_HOME")
    if explicit:
        return Path(explicit) / APP_NAME
    if is_windows():
        local = os.environ.get("LOCALAPPDATA")
        return (Path(local) if local else Path.home() / "AppData" / "Local") / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def log_file() -> Path:
    """The log file used when the process has no console (a Windows launch from the Start menu)."""
    return data_dir() / "karamws.log"


def install_dir() -> Path:
    """The folder that holds the virtual environment: /opt/karamws, the Windows install folder or a checkout."""
    return Path(sys.prefix).parent


def bundled_browsers_dir() -> Path | None:
    """The Chromium that the installation carries (``browsers`` beside the virtual environment), if there is one."""
    folder = install_dir() / _BROWSERS_FOLDER
    return folder if folder.is_dir() and any(folder.iterdir()) else None


def user_browsers_dir() -> Path:
    """Where a Chromium that the user downloaded from the program goes when the installation itself is read-only."""
    return data_dir() / _BROWSERS_FOLDER
