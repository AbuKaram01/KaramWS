# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for the GUI's pure logic (links, wording). They need PyGObject installed, nothing else."""

from collections import Counter
from pathlib import Path

import pytest

pytest.importorskip("gi")

from karamws.core import ScrapeEvent, ScrapeStatus  # noqa: E402
from karamws.gui.presentation import (  # noqa: E402
    describe_event,
    display_path,
    finish_headline,
    finish_notification,
    summarize,
)
from karamws.gui.request import normalize_url  # noqa: E402


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("example.com/post", "https://example.com/post"),
        ("  http://example.com/a  ", "http://example.com/a"),
        ("https://example.com", "https://example.com"),
        ("", None),
        ("not a url", None),
        ("ftp://example.com/file", None),
        ("http://", None),
    ],
)
def test_normalize_url(typed, expected):
    assert normalize_url(typed) == expected


def test_saved_row_shows_the_file_name():
    event = ScrapeEvent(ScrapeStatus.SAVED, "https://site.com/a", "/home/me/Articles/site.com/a-123.md")
    row = describe_event(event)
    assert (row.title, row.subtitle) == ("https://site.com/a", "a-123.md")


def test_skipped_row_explains_itself():
    event = ScrapeEvent(ScrapeStatus.SKIPPED, "https://site.com/a", "already saved")
    assert describe_event(event).subtitle == "Already saved"


def test_failed_row_shows_the_reason():
    event = ScrapeEvent(ScrapeStatus.FAILED, "https://site.com/a", "HTTP 403 for https://site.com/a")
    assert describe_event(event).subtitle == "HTTP 403 for https://site.com/a"


def test_each_status_has_its_own_icon():
    icons = {describe_event(ScrapeEvent(status, "u", "d")).icon_name for status in ScrapeStatus}
    assert len(icons) == len(ScrapeStatus)


def test_summary_counts_every_status():
    counts = Counter({ScrapeStatus.SAVED: 3, ScrapeStatus.FAILED: 1})
    assert summarize(counts) == "Saved 3 · Skipped 0 · Failed 1"


def test_finish_headline():
    assert finish_headline(cancelled=False, error=None) == "Done"
    assert finish_headline(cancelled=True, error=None) == "Stopped"
    assert finish_headline(cancelled=False, error="disk full") == "Stopped by an error: disk full"


def test_paths_inside_home_are_shortened(tmp_path):
    """Built from a real folder, so that it means the same on Windows, where the separator is a backslash."""
    assert display_path(tmp_path / "Documents" / "Articles", tmp_path) == "~/Documents/Articles"
    outside = tmp_path.parent / "elsewhere"
    assert display_path(outside, tmp_path) == str(outside)


def test_the_notification_says_how_it_went_and_with_what_result():
    counts = Counter({ScrapeStatus.SAVED: 4, ScrapeStatus.FAILED: 1})
    assert finish_notification("Done", counts) == ("KaramWS: Done", "Saved 4 · Skipped 0 · Failed 1")
    assert finish_notification("Stopped", counts)[0] == "KaramWS: Stopped"


def test_the_window_is_titled_with_the_name_of_the_program():
    window = Path(__file__).resolve().parent.parent / "src" / "karamws" / "gui" / "window.py"
    assert 'title="KaramWS"' in window.read_text(encoding="utf-8")


# --- the history, the welcome guide and the menu ---

def history_entry(outcome="done", saved=4, skipped=1, failed=2):
    from karamws.core.history import new_entry

    return new_entry("https://site.com/news/", "section", "/home/me/Articles", saved, skipped, failed, outcome)


def test_a_history_row_shows_the_link_the_counts_and_how_it_ended():
    from karamws.gui.presentation import describe_history_entry

    done = describe_history_entry(history_entry("done"))
    assert done.title == "https://site.com/news/"
    assert done.subtitle.endswith("Saved 4 · Skipped 1 · Failed 2")
    assert describe_history_entry(history_entry("stopped")).subtitle.endswith("· Stopped")
    assert describe_history_entry(history_entry("error")).subtitle.endswith("· Stopped by an error")
    assert len({describe_history_entry(history_entry(o)).icon_name for o in ("done", "stopped", "error")}) == 3


def test_the_outcome_of_a_job_is_what_the_history_records():
    from karamws.gui.presentation import job_outcome

    assert job_outcome(cancelled=False, error=None) == "done"
    assert job_outcome(cancelled=True, error=None) == "stopped"
    assert job_outcome(cancelled=False, error="disk full") == "error"
    assert job_outcome(cancelled=True, error="disk full") == "error"


def test_a_time_in_the_history_is_shown_as_a_local_date_and_hour():
    from karamws.gui.presentation import format_when

    shown = format_when("2026-11-21T10:30:00+00:00")
    assert len(shown) == len("2026-11-21 10:30") and shown.startswith("2026-11-2")
    assert format_when("not a time") == "not a time"


def test_the_welcome_guide_opens_by_itself_only_until_it_has_been_seen():
    from karamws.config import AppConfig
    from karamws.gui.welcome import mark_welcome_done, should_show_welcome

    assert should_show_welcome()
    mark_welcome_done()
    assert AppConfig.load().welcome_done and not should_show_welcome()


def test_every_entry_of_the_menu_is_an_action_the_application_defines():
    from karamws.gui.application import Application
    from karamws.gui.window import _MENU_ITEMS

    application = Application()
    for label, action in _MENU_ITEMS:
        assert action.startswith("app.") and application.lookup_action(action.removeprefix("app.")), label
    assert [label for label, _ in _MENU_ITEMS] == [
        "Download Browser…", "History", "Preferences", "Welcome Guide", "About",
    ]
