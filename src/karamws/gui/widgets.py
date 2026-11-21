# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Small widgets that more than one dialog needs."""

from collections.abc import Callable

from gi.repository import Adw, Gtk


def confirm_clear_history(parent: Gtk.Widget, on_confirmed: Callable[[], None]) -> None:
    """Ask before the history is cleared; ``on_confirmed`` runs only when the user agrees."""
    dialog = Adw.AlertDialog(
        heading="Clear the history?",
        body="The list of finished jobs is removed. The saved articles are not touched.",
    )
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("clear", "Clear")
    dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_default_response("cancel")
    dialog.set_close_response("cancel")
    dialog.connect("response", lambda _dialog, response: on_confirmed() if response == "clear" else None)
    dialog.present(parent)
