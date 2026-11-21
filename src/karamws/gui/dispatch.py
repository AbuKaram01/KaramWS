# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Running a function on the GTK main loop, from any thread."""

from collections.abc import Callable

from gi.repository import GLib


def run_on_main_thread(function: Callable, *args) -> None:
    """Call ``function(*args)`` once, soon, on the GTK main loop (the only thread that may touch widgets)."""

    def run_once() -> bool:
        function(*args)
        return GLib.SOURCE_REMOVE

    GLib.idle_add(run_once)
