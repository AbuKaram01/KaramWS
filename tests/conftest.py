# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Fixtures shared by the whole test suite.

They keep every test away from the real user's data folders and from the operating system's notifications.
"""

import pytest

from karamws import winsupport

# On Windows the DLLs of the GTK runtime are not on the DLL search path until the program registers them, so `import gi`
# fails with "DLL load failed while importing _gi" in any test module that imports it before something else has called
# this (what happened when the first GUI test module collected imported gi directly). Done here, before any test module
# is imported, so the result does not depend on the order the modules are collected in. A no-op off Windows.
winsupport.prepare_runtime()


@pytest.fixture(autouse=True)
def private_user_folders(tmp_path, monkeypatch):
    """Redirect the user's folders (settings, history, log file, a downloaded browser) to a temporary one."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local-appdata"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming-appdata"))


@pytest.fixture(autouse=True)
def no_real_toasts(request, monkeypatch):
    """Replace the Windows toast with a no-op, so that no test runs PowerShell or writes to the registry.

    On Windows a finished job raises its toast through PowerShell and the registry. The tests of the toast itself
    (test_winsupport.py) keep the real function and replace the system calls instead.
    """
    if not request.module.__name__.endswith("test_winsupport"):
        monkeypatch.setattr(winsupport, "send_toast", lambda title, body: False)
