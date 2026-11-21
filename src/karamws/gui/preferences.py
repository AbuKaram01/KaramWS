# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The Preferences dialog: the browser, the limits of a run, notifications and the history.

Every change is saved to the settings file immediately, so the dialog has no "Apply" step.
"""

from gi.repository import Adw

from ..config import MAX_HISTORY_LIMIT, MIN_HISTORY_LIMIT, AppConfig, update_saved_config
from ..core.history import HistoryStore
from .browser_download import BrowserDownloads, BrowserRow
from .widgets import confirm_clear_history

_MAX_ARTICLES_LIMIT = 100_000
_MAX_DELAY_SECONDS = 30


def _switch_row(title: str, subtitle: str, active: bool, setting: str) -> Adw.SwitchRow:
    """A switch that saves ``setting`` as soon as it is flipped."""
    row = Adw.SwitchRow(title=title, subtitle=subtitle, active=active)
    row.connect("notify::active", lambda switch, _param: update_saved_config(**{setting: switch.get_active()}))
    return row


def _spin_row(title: str, subtitle: str, value: float, bounds: tuple[float, float, float], setting: str,
              digits: int = 0) -> Adw.SpinRow:
    """A number box that saves ``setting`` as soon as it changes."""
    row = Adw.SpinRow.new_with_range(*bounds)
    row.set_title(title)
    row.set_subtitle(subtitle)
    row.set_digits(digits)
    row.set_value(value)
    convert = float if digits else int
    row.connect("notify::value", lambda spin, _param: update_saved_config(**{setting: convert(spin.get_value())}))
    return row


class PreferencesDialog(Adw.PreferencesDialog):
    """Where the user changes how KaramWS behaves.

    Args:
        downloads: The application's browser download manager, so a download goes on when this dialog is closed.
        history: The history of finished jobs (for the "Clear history" button).
    """

    def __init__(self, downloads: BrowserDownloads, history: HistoryStore) -> None:
        super().__init__(title="Preferences", search_enabled=False)
        self._history = history
        config = AppConfig.load()

        page = Adw.PreferencesPage()
        self.add(page)
        # The browser comes first: "Download Browser…" in the menu opens this dialog with it in view.
        page.add(self._browser_group(config, downloads))
        page.add(self._articles_group(config))
        page.add(self._notifications_group(config))
        page.add(self._history_group(config))

    def _browser_group(self, config: AppConfig, downloads: BrowserDownloads) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title="Browser",
            description="Pages that only show their content after JavaScript runs are read with a real browser.",
        )
        group.add(_switch_row(
            "Use a real browser for JavaScript pages", "Slower, and only used when a page needs it",
            config.use_browser_fallback, "use_browser_fallback",
        ))
        self._browser_row = BrowserRow(downloads, self.add_toast_text)
        self.connect("closed", lambda _dialog: self._browser_row.detach())
        group.add(self._browser_row)
        return group

    def _articles_group(self, config: AppConfig) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Articles", description="How a run behaves.")
        group.add(_spin_row(
            "Stop after this many articles", "0 means no limit",
            config.max_articles, (0, _MAX_ARTICLES_LIMIT, 10), "max_articles",
        ))
        group.add(_spin_row(
            "Pause between requests (seconds)", "Be kind to the sites you read",
            config.request_delay_seconds, (0, _MAX_DELAY_SECONDS, 0.5), "request_delay_seconds", digits=1,
        ))
        group.add(_switch_row(
            "Follow the site's robots.txt", "Skip pages the site asks bots not to visit",
            config.respect_robots, "respect_robots",
        ))
        return group

    def _notifications_group(self, config: AppConfig) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Notifications")
        group.add(_switch_row(
            "Notify me when it finishes", "A desktop notification, only when KaramWS is not in front",
            config.notify_when_done, "notify_when_done",
        ))
        return group

    def _history_group(self, config: AppConfig) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="History", description="The jobs that ended, in Menu > History.")
        group.add(_switch_row(
            "Keep a history of finished jobs", "Lets you run a job again, or open its folder",
            config.history_enabled, "history_enabled",
        ))
        group.add(_spin_row(
            "Jobs to keep", "The oldest are removed first",
            config.history_keep, (MIN_HISTORY_LIMIT, MAX_HISTORY_LIMIT, 10), "history_limit",
        ))
        clear = Adw.ActionRow(title="Clear the history", subtitle="Removes the list only, never the saved articles",
                              activatable=True)
        clear.connect("activated", lambda _row: confirm_clear_history(self, self._clear_history))
        group.add(clear)
        return group

    def add_toast_text(self, message: str) -> None:
        """Show a short message at the bottom of the dialog."""
        self.add_toast(Adw.Toast(title=message))

    def _clear_history(self) -> None:
        self._history.clear()
        self.add_toast_text("History cleared.")
