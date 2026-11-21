# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Where the program keeps things, and where it looks for the Chromium that came with the installation."""

import sys
from pathlib import Path

from karamws.core import fetching, paths


def environment_with_browsers(tmp_path: Path, monkeypatch, *, populated: bool = True) -> Path:
    """An installation folder: a virtual environment (sys.prefix) with a ``browsers`` folder beside it."""
    monkeypatch.setattr(sys, "prefix", str(tmp_path / ".venv"))
    browsers = tmp_path / "browsers"
    browsers.mkdir()
    if populated:
        (browsers / "chromium_headless_shell-1243").mkdir()
    return browsers


def test_chromium_is_looked_for_beside_the_virtual_environment(tmp_path, monkeypatch):
    browsers = environment_with_browsers(tmp_path, monkeypatch)
    assert paths.bundled_browsers_dir() == browsers


def test_an_empty_or_missing_browsers_folder_means_there_is_no_bundled_chromium(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "prefix", str(tmp_path / ".venv"))
    assert paths.bundled_browsers_dir() is None
    (tmp_path / "browsers").mkdir()
    assert paths.bundled_browsers_dir() is None


def test_the_playwright_variable_points_at_the_bundled_chromium(tmp_path, monkeypatch):
    browsers = environment_with_browsers(tmp_path, monkeypatch)
    monkeypatch.delenv(paths.BROWSERS_ENV, raising=False)
    fetching._use_bundled_browsers()
    assert Path(fetching.os.environ[paths.BROWSERS_ENV]) == browsers


def test_a_setting_of_the_user_wins_over_the_bundled_chromium(tmp_path, monkeypatch):
    environment_with_browsers(tmp_path, monkeypatch)
    monkeypatch.setenv(paths.BROWSERS_ENV, "/somewhere/else")
    fetching._use_bundled_browsers()
    assert fetching.os.environ[paths.BROWSERS_ENV] == "/somewhere/else"


def test_without_a_bundled_chromium_playwright_keeps_its_own_default(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "prefix", str(tmp_path / ".venv"))
    monkeypatch.delenv(paths.BROWSERS_ENV, raising=False)
    fetching._use_bundled_browsers()
    assert paths.BROWSERS_ENV not in fetching.os.environ


def test_the_data_folder_follows_xdg_data_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert paths.data_dir() == tmp_path / "data" / "karamws"
    assert paths.log_file() == tmp_path / "data" / "karamws" / "karamws.log"


def test_on_windows_the_data_folder_is_under_local_app_data(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setattr(paths, "is_windows", lambda: True)
    assert paths.data_dir() == tmp_path / "local" / "karamws"
