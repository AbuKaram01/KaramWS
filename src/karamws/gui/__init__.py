# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""GTK4 + libadwaita front-end for KaramWS.

Requires GTK 4.10+ and libadwaita 1.5+ (for Gtk.FileDialog, Adw.Dialog, Adw.PreferencesDialog, Adw.AboutDialog,
Adw.ToolbarView, Adw.EntryRow / Adw.SpinRow /
Adw.SwitchRow). See the project README for install instructions.
"""

from .. import winsupport

# On Windows the GTK runtime has to be made visible before ``gi`` is imported by any submodule.
winsupport.prepare_runtime()

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
except (ImportError, ValueError) as error:
    winsupport.report_missing_toolkit(error)
    raise
