# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Finding Chromium and downloading it (with a stand-in for ``playwright install chromium``)."""

import sys
import threading
import time

import pytest

from karamws.core import browser, paths
from karamws.core.browser import BrowserInstallCancelled, BrowserInstallError, ChromiumInstaller


def make_chromium(folder):
    (folder / "chromium_headless_shell-1243").mkdir(parents=True)


def installation(tmp_path, monkeypatch):
    """A virtual environment (sys.prefix) with an installation folder around it."""
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "install" / ".venv"))
    (tmp_path / "install").mkdir()
    return tmp_path / "install"


def test_chromium_is_found_beside_the_environment(tmp_path, monkeypatch):
    make_chromium(installation(tmp_path, monkeypatch) / "browsers")
    assert browser.chromium_home() == tmp_path / "install" / "browsers"
    assert browser.chromium_ready()


def test_chromium_the_user_downloaded_is_found_in_the_data_folder(tmp_path, monkeypatch):
    installation(tmp_path, monkeypatch)
    make_chromium(paths.user_browsers_dir())
    assert browser.chromium_home() == paths.user_browsers_dir()


def test_a_folder_without_the_headless_chromium_does_not_count(tmp_path, monkeypatch):
    (installation(tmp_path, monkeypatch) / "browsers" / "chromium-1243").mkdir(parents=True)  # only the full browser
    assert browser.chromium_home() is None


def test_playwrights_own_folder_makes_it_ready_too(tmp_path, monkeypatch):
    installation(tmp_path, monkeypatch)
    monkeypatch.delenv(paths.BROWSERS_ENV, raising=False)
    # Where Playwright keeps its browsers by default: under the cache folder on Linux, under LOCALAPPDATA on Windows.
    # The test names both, so that it means the same on either system.
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    assert not browser.chromium_ready()
    default_folder = tmp_path / ("local" if paths.is_windows() else "cache") / "ms-playwright"
    make_chromium(default_folder)
    assert browser.chromium_ready()


def test_a_browsers_folder_named_by_the_user_is_the_one_that_counts(tmp_path, monkeypatch):
    installation(tmp_path, monkeypatch)
    explicit = tmp_path / "my-browsers"
    monkeypatch.setenv(paths.BROWSERS_ENV, str(explicit))
    assert not browser.chromium_ready()
    make_chromium(explicit)
    assert browser.chromium_ready()


def test_a_download_goes_beside_the_environment_when_that_can_be_written(tmp_path, monkeypatch):
    install = installation(tmp_path, monkeypatch)
    assert browser.install_target() == install / "browsers"


def test_a_download_goes_to_the_users_folder_when_the_installation_is_read_only(tmp_path, monkeypatch):
    installation(tmp_path, monkeypatch)
    monkeypatch.setattr(browser.os, "access", lambda *_: False)
    assert browser.install_target() == paths.user_browsers_dir()


@pytest.mark.parametrize(("line", "percent"), [
    ("|■■■■■■■■                |  40% of 150.2 MiB", 40),
    ("|■■■■■■■■■■■■■■■■■■■■■■■■| 100% of 94.1 MiB", 100),
    ("Downloading Chromium 153.0.7500.2 (playwright build v1243)", None),
])
def test_the_progress_is_read_from_the_output(line, percent):
    assert browser.percent_in(line) == percent


def fake_playwright(tmp_path, body: str):
    script = tmp_path / "fake_playwright.py"
    script.write_text(
        "import os, sys, time\nfrom pathlib import Path\ntarget = Path(os.environ['PLAYWRIGHT_BROWSERS_PATH'])\n" + body
    )
    return (sys.executable, str(script))


def test_a_download_reports_its_output_and_leaves_chromium_in_the_target(tmp_path):
    command = fake_playwright(tmp_path, "print('  20% of 100 MiB'); print('  100% of 100 MiB')\n"
                                        "(target / 'chromium_headless_shell-1243').mkdir(parents=True)\n")
    lines: list[str] = []
    installer = ChromiumInstaller(tmp_path / "browsers", command)
    installer.run(lines.append)
    assert lines == ["20% of 100 MiB", "100% of 100 MiB"]
    assert browser.has_chromium(tmp_path / "browsers")


def test_a_failed_download_says_what_the_program_printed(tmp_path):
    command = fake_playwright(tmp_path, "print('Error: getaddrinfo ENOTFOUND cdn.playwright.dev'); sys.exit(1)\n")
    with pytest.raises(BrowserInstallError, match="ENOTFOUND"):
        ChromiumInstaller(tmp_path / "browsers", command).run(lambda line: None)


def test_a_download_that_ends_without_chromium_is_an_error(tmp_path):
    command = fake_playwright(tmp_path, "print('done')\n")
    with pytest.raises(BrowserInstallError):
        ChromiumInstaller(tmp_path / "browsers", command).run(lambda line: None)


def test_a_download_can_be_stopped(tmp_path):
    command = fake_playwright(tmp_path, "print('starting', flush=True)\ntime.sleep(60)\n")
    installer = ChromiumInstaller(tmp_path / "browsers", command)
    started = threading.Event()
    outcome = []

    def work():
        try:
            installer.run(lambda line: started.set())
        except BrowserInstallCancelled:
            outcome.append("cancelled")

    thread = threading.Thread(target=work)
    thread.start()
    assert started.wait(10)
    began = time.monotonic()
    installer.cancel()
    thread.join(10)
    assert outcome == ["cancelled"] and time.monotonic() - began < 8
