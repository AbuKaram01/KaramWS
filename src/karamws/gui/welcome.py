# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The first-run welcome guide: what KaramWS does, getting its browser, and where the articles go.

The guide has three pages::

    1. Welcome   what the program does, in three lines
    2. Browser   the Chromium for JavaScript pages: whether it is there, and a button to download it
    3. Finish    where the articles are saved, and what is ready

It opens by itself the first time KaramWS starts, and from the menu ("Welcome Guide") whenever the user wants it
again. The download belongs to the application, so pressing Close while it runs does not interrupt it.
"""

from pathlib import Path

from gi.repository import Adw, Gdk, Gtk

from ..config import AppConfig, update_saved_config
from ..core.browser import chromium_ready, install_target
from .browser_download import BrowserDownloads, BrowserEvent, BrowserEventKind, BrowserRow
from .folders import choose_folder, saved_output_dir
from .presentation import display_path

# Positions of the pages in the carousel.
_PAGE_WELCOME, _PAGE_BROWSER, _PAGE_FINISH = 0, 1, 2
# Shown instead of the application icon when the icon theme does not provide it.
_FALLBACK_ICON = "web-browser-symbolic"

# The rows of the welcome page: icon name, title and description.
_FEATURES = (
    ("web-browser-symbolic", "Articles, sections and websites",
     "Paste a link to one article, a category page or a whole website. KaramWS finds the articles and saves each one "
     "as a Markdown file."),
    ("emblem-documents-symbolic", "Pages that need JavaScript",
     "Some sites only show their text after JavaScript runs. KaramWS opens those in a real browser (Chromium) when "
     "it has to."),
    ("security-high-symbolic", "Private and polite",
     "Everything runs on your computer. KaramWS follows each site's robots.txt and pauses between requests."),
)


def should_show_welcome() -> bool:
    """Whether the guide opens by itself at start-up: only for someone who has not seen it yet."""
    return not AppConfig.load().welcome_done


def mark_welcome_done() -> None:
    """Record that the guide has been dealt with, so that it does not come back by itself."""
    if not AppConfig.load().welcome_done:
        update_saved_config(welcome_done=True)


def _scrolled(content: Gtk.Widget) -> Gtk.ScrolledWindow:
    """Wrap ``content`` as a page body: centred, in a comfortable column, scrolling when the dialog is short."""
    clamp = Adw.Clamp(maximum_size=460, tightening_threshold=360, margin_start=12, margin_end=12)
    clamp.set_child(content)
    # hexpand is needed because a carousel gives a page only its natural width unless the page asks for all of it.
    return Gtk.ScrolledWindow(child=clamp, hscrollbar_policy=Gtk.PolicyType.NEVER, hexpand=True, vexpand=True)


class WelcomeDialog(Adw.Dialog):
    """The welcome guide dialog.

    Args:
        downloads: The application's browser download manager, so the download continues when the guide is closed.
        app_icon: Name of the application icon shown on the first page.
    """

    def __init__(self, downloads: BrowserDownloads, *, app_icon: str) -> None:
        super().__init__(title="Welcome", content_width=520, content_height=700)
        self._downloads = downloads
        self._app_icon = app_icon
        self._index = _PAGE_WELCOME

        self._carousel = Adw.Carousel(
            interactive=False, allow_scroll_wheel=False, allow_mouse_drag=False, allow_long_swipes=False, vexpand=True,
        )
        self._pages = [self._welcome_page(), self._browser_page(), self._finish_page()]
        for page in self._pages:
            self._carousel.append(page)

        toolbar = Adw.ToolbarView(content=self._build_body())
        toolbar.add_top_bar(Adw.HeaderBar(show_title=False))
        toolbar.set_top_bar_style(Adw.ToolbarStyle.FLAT)
        self.set_child(toolbar)
        self.set_default_widget(self._next)

        self._update_finish_page()
        self._sync_buttons()
        downloads.subscribe(self._on_event)
        self.connect("closed", self._on_closed)

    # --- Building ---

    def _build_body(self) -> Gtk.Box:
        # The toasts sit on the pages, so they never cover the Back / Next buttons.
        self._toasts = Adw.ToastOverlay(child=self._carousel, vexpand=True)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        body.append(self._toasts)
        body.append(Adw.CarouselIndicatorDots(carousel=self._carousel, margin_top=6, margin_bottom=6))
        body.append(self._build_buttons())
        return body

    def _build_buttons(self) -> Gtk.Box:
        self._back = Gtk.Button(label="Back", css_classes=["flat", "pill"])
        self._back.connect("clicked", lambda _button: self._go(self._index - 1))
        self._next = Gtk.Button(label="Next", css_classes=["suggested-action", "pill"], width_request=180)
        self._next.connect("clicked", self._on_next)
        buttons = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER, margin_top=6, margin_bottom=24)
        buttons.append(self._back)
        buttons.append(self._next)
        return buttons

    # --- Pages ---

    def _welcome_page(self) -> Gtk.Widget:
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icon = self._app_icon if theme.has_icon(self._app_icon) else _FALLBACK_ICON
        features = Adw.PreferencesGroup(margin_top=6, margin_bottom=12)
        for icon_name, title, subtitle in _FEATURES:
            row = Adw.ActionRow(title=title, subtitle=subtitle, subtitle_lines=0, activatable=False)
            row.add_prefix(Gtk.Image(icon_name=icon_name, icon_size=Gtk.IconSize.LARGE))
            features.add(row)
        page = Adw.StatusPage(
            icon_name=icon, title="Welcome to KaramWS",
            description="Save the articles of any website as files on your own computer.",
            child=features,
        )
        return _scrolled(page)

    def _browser_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=12, margin_bottom=12)
        box.append(Gtk.Label(label="Get the browser", css_classes=["title-1"], wrap=True))
        box.append(Gtk.Label(
            label=(
                "Some pages only show their text after JavaScript runs. KaramWS reads those with Chromium, "
                "downloaded once and kept on your computer. You can skip this if you only read simple pages."
            ),
            wrap=True, justify=Gtk.Justification.CENTER, css_classes=["dim-label"],
        ))
        group = Adw.PreferencesGroup(title="Browser")
        self._browser_row = BrowserRow(self._downloads, self.add_toast_text)
        group.add(self._browser_row)
        box.append(group)
        box.append(Gtk.Label(
            label=f"Saved to {display_path(install_target(), Path.home())}. The download carries on in the "
                  "background if you close this guide. You can also do it later from the menu: Download Browser.",
            wrap=True, xalign=0, css_classes=["caption", "dim-label"],
        ))
        return _scrolled(box)

    def _finish_page(self) -> Gtk.Widget:
        self._folder_row = Adw.ActionRow(title="Save articles to", use_markup=False, activatable=True)
        self._folder_row.add_suffix(Gtk.Image(icon_name="folder-open-symbolic"))
        self._folder_row.connect("activated", lambda _row: choose_folder(self, self._on_folder_chosen))
        self._show_folder(saved_output_dir(AppConfig.load()))
        group = Adw.PreferencesGroup(margin_top=12, margin_bottom=12)
        group.add(self._folder_row)
        self._finish = Adw.StatusPage(icon_name="object-select-symbolic", title="You're all set", child=group)
        return _scrolled(self._finish)

    # --- State ---

    def add_toast_text(self, message: str) -> None:
        """Show a short message on the pages."""
        self._toasts.add_toast(Adw.Toast(title=message))

    def _show_folder(self, folder: Path) -> None:
        self._folder_row.set_subtitle(display_path(folder, Path.home()))

    def _on_folder_chosen(self, folder: Path) -> None:
        update_saved_config(output_dir=str(folder))
        self._show_folder(folder)

    def _update_finish_page(self) -> None:
        if chromium_ready():
            description = "Paste a link and press Start. Pages that need JavaScript are ready too."
        else:
            description = ("Paste a link and press Start. Pages that need JavaScript will need the browser: "
                           "download it any time from the menu.")
        self._finish.set_description(description)

    def _on_event(self, event: BrowserEvent) -> None:
        if event.kind is not BrowserEventKind.PROGRESS:
            self._update_finish_page()
        self._sync_buttons()

    # --- Moving between the pages ---

    def _go(self, index: int) -> None:
        self._index = min(max(index, _PAGE_WELCOME), _PAGE_FINISH)
        self._carousel.scroll_to(self._pages[self._index], True)
        self._sync_buttons()

    def _on_next(self, _button: Gtk.Button) -> None:
        if self._index == _PAGE_FINISH:
            self.close()
        else:
            self._go(self._index + 1)

    def _sync_buttons(self) -> None:
        self._back.set_visible(self._index != _PAGE_WELCOME)
        if self._index == _PAGE_FINISH:
            label = "Get Started"
        elif self._index == _PAGE_BROWSER and not chromium_ready() and not self._downloads.running:
            label = "Skip for Now"
        else:
            label = "Next"
        self._next.set_label(label)

    def _on_closed(self, _dialog: Adw.Dialog) -> None:
        self._downloads.unsubscribe(self._on_event)
        self._browser_row.detach()
        mark_welcome_done()
