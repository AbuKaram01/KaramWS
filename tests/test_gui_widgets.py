# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The real widgets: the form, Preferences, the history and the welcome guide. They need GTK and a display."""

import pytest

pytest.importorskip("gi")

import karamws.gui  # noqa: F401,E402  (pins the GTK versions)
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from karamws import APP_ID  # noqa: E402
from karamws.config import AppConfig  # noqa: E402
from karamws.core import UrlKind  # noqa: E402
from karamws.core.history import HistoryStore, new_entry  # noqa: E402
from karamws.gui import browser_download  # noqa: E402
from karamws.gui.browser_download import BrowserDownloads, BrowserRow  # noqa: E402
from karamws.gui.form import LinkForm  # noqa: E402
from karamws.gui.history_dialog import HistoryDialog  # noqa: E402
from karamws.gui.preferences import PreferencesDialog  # noqa: E402
from karamws.gui.welcome import WelcomeDialog  # noqa: E402

if Gdk.Display.get_default() is None:
    pytest.skip("needs a display (run under xvfb-run)", allow_module_level=True)

Adw.init()


def walk(widget, kind):
    """Every widget of ``kind`` inside ``widget``, depth first.

    A dialog that has not been shown keeps its content outside the widget tree, so a preferences dialog is walked
    through its page (``get_visible_page``); ``contents`` does that.
    """
    child = widget.get_first_child()
    while child is not None:
        if isinstance(child, kind):
            yield child
        yield from walk(child, kind)
        child = child.get_next_sibling()


def contents(dialog):
    """The page of a preferences dialog, which holds all of its rows."""
    return dialog.get_visible_page()


def row_titled(dialog, kind, title):
    return next(row for row in walk(contents(dialog), kind) if row.get_title() == title)


def preferences():
    return PreferencesDialog(BrowserDownloads(), HistoryStore())


# --- the form ---

def test_the_form_builds_a_request_from_the_link_and_the_saved_settings():
    AppConfig(max_articles=12, request_delay_seconds=0.5, respect_robots=False).save()
    form = LinkForm(on_submit=lambda: None)
    form._url.set_text("example.com/news")
    request = form.build_request()
    assert request.url == "https://example.com/news" and request.kind is None
    assert (request.config.max_articles, request.config.request_delay_seconds) == (12, 0.5)
    assert request.config.respect_robots is False


def test_an_unusable_link_is_flagged_and_gives_no_request():
    form = LinkForm(on_submit=lambda: None)
    form._url.set_text("not a link")
    assert form.build_request() is None
    assert form._url.has_css_class("error")


def test_the_form_can_be_filled_from_the_history(tmp_path):
    form = LinkForm(on_submit=lambda: None)
    form.set_fields("https://site.com/news/", UrlKind.SECTION, tmp_path)
    request = form.build_request()
    assert (request.url, request.kind, request.output_dir) == ("https://site.com/news/", UrlKind.SECTION, tmp_path)


def test_the_folder_saved_last_time_is_the_folder_of_the_next_start(tmp_path):
    AppConfig(output_dir=str(tmp_path)).save()
    assert LinkForm(on_submit=lambda: None).output_dir == tmp_path


# --- Preferences: every change is saved at once ---

def test_a_switch_in_preferences_is_saved_when_it_is_flipped():
    row = row_titled(preferences(), Adw.SwitchRow, "Follow the site's robots.txt")
    row.set_active(False)
    assert AppConfig.load().respect_robots is False
    row.set_active(True)
    assert AppConfig.load().respect_robots is True


def test_a_number_in_preferences_is_saved_when_it_changes():
    dialog = preferences()
    row_titled(dialog, Adw.SpinRow, "Stop after this many articles").set_value(25)
    row_titled(dialog, Adw.SpinRow, "Pause between requests (seconds)").set_value(2.5)
    saved = AppConfig.load()
    assert (saved.max_articles, saved.request_delay_seconds) == (25, 2.5)


def test_preferences_shows_what_is_saved():
    AppConfig(notify_when_done=False, max_articles=7).save()
    dialog = preferences()
    assert row_titled(dialog, Adw.SwitchRow, "Notify me when it finishes").get_active() is False
    assert row_titled(dialog, Adw.SpinRow, "Stop after this many articles").get_value() == 7


def test_everything_the_old_advanced_section_offered_is_in_preferences():
    dialog = preferences()
    titles = {row.get_title() for kind in (Adw.SwitchRow, Adw.SpinRow) for row in walk(contents(dialog), kind)}
    assert {
        "Stop after this many articles", "Pause between requests (seconds)", "Follow the site's robots.txt",
        "Use a real browser for JavaScript pages", "Notify me when it finishes",
    } <= titles


# --- the browser row ---

@pytest.mark.parametrize(("ready", "words", "button"), [(True, "Ready", False), (False, "Not installed", True)])
def test_the_browser_row_says_whether_chromium_is_there(monkeypatch, ready, words, button):
    monkeypatch.setattr(browser_download, "chromium_ready", lambda: ready)
    row = BrowserRow(BrowserDownloads(), lambda message: None)
    assert words in row.get_subtitle()
    assert row._button.get_visible() is button


# --- the history ---

def test_the_history_lists_jobs_and_lets_one_be_forgotten(tmp_path):
    history = HistoryStore(tmp_path / "history.json")
    keep = new_entry("https://keep.com/", "auto", "/x", 1, 0, 0, "done")
    drop = new_entry("https://drop.com/", "site", "/y", 2, 0, 0, "done")
    history.add(keep, 10)
    history.add(drop, 10)
    dialog = HistoryDialog(history, lambda entry: True, lambda folder: None)
    assert len(dialog._rows) == 2
    dialog._forget(drop)
    assert [e.url for e in history.entries()] == ["https://keep.com/"] and len(dialog._rows) == 1


def test_an_empty_history_shows_the_empty_page(tmp_path):
    dialog = HistoryDialog(HistoryStore(tmp_path / "history.json"), lambda entry: True, lambda folder: None)
    assert dialog._stack.get_visible_child_name() == "empty" and not dialog._clear_button.get_sensitive()


def test_using_an_entry_again_hands_it_to_the_window(tmp_path):
    history = HistoryStore(tmp_path / "history.json")
    entry = new_entry("https://again.com/", "article", "/z", 1, 0, 0, "done")
    history.add(entry, 10)
    handed = []
    dialog = HistoryDialog(history, lambda picked: handed.append(picked) or False, lambda folder: None)
    dialog._use(entry)
    assert handed == [entry]


# --- the welcome guide ---

def test_closing_the_welcome_guide_records_that_it_was_seen():
    dialog = WelcomeDialog(BrowserDownloads(), app_icon=APP_ID)
    assert not AppConfig.load().welcome_done
    dialog.emit("closed")
    assert AppConfig.load().welcome_done


def test_the_welcome_guide_has_the_three_pages_and_walks_through_them():
    dialog = WelcomeDialog(BrowserDownloads(), app_icon=APP_ID)
    assert len(dialog._pages) == 3 and not dialog._back.get_visible()
    dialog._go(2)
    assert dialog._back.get_visible() and dialog._next.get_label() == "Get Started"
    dialog._go(1)
    assert dialog._next.get_label() in ("Next", "Skip for Now")


def test_the_folder_chosen_in_the_welcome_guide_is_saved(tmp_path):
    dialog = WelcomeDialog(BrowserDownloads(), app_icon=APP_ID)
    dialog._on_folder_chosen(tmp_path)
    assert AppConfig.load().output_dir == str(tmp_path)


def test_gtk_is_really_loaded_with_the_versions_the_project_needs():
    assert Gtk.get_major_version() == 4 and Adw.get_minor_version() >= 5
