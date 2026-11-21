# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Which GTK release is used, and what the installer and the CI jobs leave behind when an installation fails."""

from packaging_support import ROOT, WINDOWS


def test_the_gtk_release_is_a_tested_one_and_not_the_newest():
    portable = (ROOT / "scripts" / "gtk-portable.ps1").read_text(encoding="utf-8")
    # gvsbuild 2026.10.0 builds its PyGObject wheels for Python 3.15; 2026.8.0 has them for 3.14, which is what CI uses.
    assert "$script:GtkDefaultTag = '2026.8.0'" in portable
    assert "python-version: \"3.14\"" in (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    install = (ROOT / "scripts" / "install-windows.ps1").read_text(encoding="utf-8")
    assert "Get-GtkZipUrls" not in install and "releases/latest" not in install  # No "newest" lookup of its own.
    assert "[string]$GtkTag" in install and "-Tag $GtkTag" in install
    build = (ROOT / "packaging" / "build-windows.ps1").read_text(encoding="utf-8")
    assert "[string]$GtkTag = ''" in build


def test_a_wheel_mismatch_says_which_python_the_wheels_are_for():
    install = (ROOT / "scripts" / "install-windows.ps1").read_text(encoding="utf-8")
    assert "are for Python $($available -join ', ')" in install and "-GtkTag" in install


def test_the_installer_keeps_a_log_of_the_install_script_and_points_to_it():
    install = (ROOT / "scripts" / "install-windows.ps1").read_text(encoding="utf-8")
    assert "[string]$LogFile" in install and "Start-Transcript" in install
    iss = (WINDOWS / "karamws.iss").read_text(encoding="utf-8")
    assert "-LogFile" in iss and "karamws\\install.log" in iss
    # Passed to the script, named in the error.
    assert iss.count("install.log") >= 2


def test_the_manual_installer_job_cannot_hang_and_shows_the_logs():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job = ci.split("windows-installer-run:")[1]
    assert job.count("run-installer.ps1") == 2 and job.count("timeout-minutes: 35") == 2
    script = (WINDOWS / "run-installer.ps1").read_text(encoding="utf-8")
    assert "WaitForExit($TimeoutMinutes * 60 * 1000)" in script and "taskkill" in script
    assert script.index("finally") < script.index("Get-Content $scriptLog")  # The logs show on failure too.


def test_the_installer_is_built_with_everything_inside_and_checked_for_it():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for job in (ci.split("  installer:")[1].split("  windows-installer-run:")[0],
                ci.split("  windows-installer-run:")[1]):
        # The build fails, instead of quietly leaving something out.
        assert "-RequirePython -RequireBrowsers -RequireVcRuntime" in job
    built = ci.split("  installer:")[1].split("  windows-installer-run:")[0]
    for carried in ("The installer carries the GTK runtime", "The installer carries the Python installer",
                    "The installer carries Chromium"):
        assert carried in built, carried


def test_the_linux_package_is_installed_and_used_in_ci_with_nothing_configured():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job = ci.split("  linux-package:")[1].split("  windows-core:")[0]
    assert "./packaging/build.sh" in job and "apt-get install -y ./packaging/dist/karamws_" in job
    # The program has to find the Chromium of the package by itself.
    assert "env -u PLAYWRIGHT_BROWSERS_PATH karamws" in job
    assert "test ! -e /opt/karamws" in job  # Removing it leaves nothing behind.


def test_the_manual_job_looks_for_dlls_the_installation_does_not_provide():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job = ci.split("  windows-installer-run:")[1]
    assert "dlls.py scan --app $app --strict" in job and "dlls.py loaded --app $app --strict" in job
    assert "Programs\\KaramWS" in job


def test_a_failing_native_command_is_never_the_exit_code_of_a_step_that_otherwise_passed():
    """Actions ends a pwsh step with the exit code of the last native command: taskkill fails when part of the process
    tree is already gone. That is a result here, not a failure."""
    checker = (WINDOWS / "check-installed.ps1").read_text(encoding="utf-8")
    assert "$global:LASTEXITCODE = 0" in checker.split('cmd /c "taskkill')[1].split("\n")[0]
