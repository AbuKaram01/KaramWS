# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Which GTK release is used, and what the installer and the CI jobs leave behind when an installation fails."""

import ast
import json
import re
import subprocess

import pytest
from packaging_support import ROOT, WINDOWS, needs_pwsh


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
    # The runner's package lists can be stale (a 404 for a dependency in a real run): refresh them first.
    assert job.index("sudo apt-get update") < job.index("apt-get install -y ./packaging/dist/karamws_")
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


# --- the workflow itself ---

def workflow_text() -> str:
    return (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def pwsh_steps() -> dict[str, str]:
    """Every PowerShell step of the workflow, by job and name, as the script PowerShell is given."""
    yaml = pytest.importorskip("yaml")
    steps = {}
    for job_name, job in yaml.safe_load(workflow_text())["jobs"].items():
        for number, step in enumerate(job["steps"]):
            if step.get("shell") == "pwsh" and "run" in step:
                # GitHub fills the ${{ ... }} expressions in before PowerShell sees the script.
                steps[f"{job_name} / {step.get('name', number)}"] = re.sub(r"\$\{\{.*?\}\}", "0", step["run"])
    return steps


PARSE_STEPS = """\
param([Parameter(Mandatory)][string]$StepsFile)
$steps = Get-Content -LiteralPath $StepsFile -Raw | ConvertFrom-Json
$checked = 0
$bad = 0
foreach ($step in $steps.PSObject.Properties) {
    $errors = $null
    $tokens = $null
    [System.Management.Automation.Language.Parser]::ParseInput($step.Value, [ref]$tokens, [ref]$errors) | Out-Null
    $checked++
    if ($errors.Count) { $bad++; Write-Output ('FAIL ' + $step.Name + ': ' + $errors[0].Message) }
}
Write-Output "checked $checked steps"
if ($checked -eq 0 -or $bad) { exit 1 }
"""


def parse_with_powershell(tmp_path, steps: dict[str, str]) -> subprocess.CompletedProcess:
    """Run PowerShell's own parser over ``steps``.

    The steps go in a file and the parser is run with ``-File``, so that the file name reaches the script as an
    argument. (With ``-Command`` the name was added to the command line as a command of its own: on Linux PowerShell
    then opened the document with xdg-open, which on a machine with a browser waits for ever, and the check checked
    nothing.) Nothing can wait for an answer: no input is given and the run has a time limit.
    """
    (tmp_path / "steps.json").write_text(json.dumps(steps), encoding="utf-8")
    (tmp_path / "parse.ps1").write_text(PARSE_STEPS, encoding="utf-8")
    return subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-File", str(tmp_path / "parse.ps1"), str(tmp_path / "steps.json")],
        capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL, timeout=120,
    )


@needs_pwsh
def test_every_powershell_step_of_the_workflow_parses(tmp_path):
    """A mistake in a step is only found by running the workflow, which costs a trip to GitHub: parse them here."""
    steps = pwsh_steps()
    assert len(steps) > 20  # the workflow really has that many; an empty result must not pass for a success
    result = parse_with_powershell(tmp_path, steps)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"checked {len(steps)} steps" in result.stdout


@needs_pwsh
def test_the_check_of_the_steps_really_notices_a_broken_step(tmp_path):
    """The check once passed without reading anything: prove that it fails when it should."""
    result = parse_with_powershell(tmp_path, {"fine": "Write-Output 1", "broken": "if ($x { oops"})
    assert result.returncode == 1
    assert "FAIL broken" in result.stdout and "FAIL fine" not in result.stdout


def test_the_python_programs_inside_the_workflow_steps_are_valid_python():
    for name, script in pwsh_steps().items():
        for program in re.findall(r"@'\n(.*?)\n'@", script, re.S):
            ast.parse(program)  # a SyntaxError here names the step in the traceback's locals; the loop shows which


def test_the_full_install_job_is_manual_and_installs_with_nothing_carried_by_an_installer():
    ci = workflow_text()
    job = ci.split("  windows-full-install:")[1]
    assert "github.event_name == 'workflow_dispatch'" in job.split("steps:")[0]
    assert "timeout-minutes: 60" in job
    # Nothing is skipped: GTK, Python's libraries and Chromium are all downloaded by the install script.
    assert "./scripts/install-windows.ps1 -PythonVersion 3.14" in job and "-SkipBrowser" not in job
    for step in ("The Start menu entry points at something that exists", "A real scrape on Windows",
                 "Arabic letters in every path", "Test suite with the real libraries", "Launch the application"):
        assert step in job, step


def test_the_arabic_letters_check_puts_one_in_every_place_a_file_goes():
    job = workflow_text().split("  windows-full-install:")[1]
    for variable in ("$env:TEMP", "$env:XDG_DATA_HOME", "$env:XDG_CONFIG_HOME", "$env:PLAYWRIGHT_BROWSERS_PATH"):
        assert variable in job, variable
    assert "Copy-Item (Join-Path (Get-Location) 'browsers')" in job  # Chromium itself runs from the Arabic folder
    assert "[char[]](0x0623, 0x062D, 0x0645, 0x062F)" in job  # no Arabic letters typed into the YAML


def test_the_full_install_job_stops_what_it_started_and_ignores_taskkill_exit_codes():
    job = workflow_text().split("  windows-full-install:")[1]
    assert job.count("Stop-Process -Id $server.Id") == 2  # in a finally, so a failed step leaves no server behind
    assert "$global:LASTEXITCODE = 0" in job.split('cmd /c "taskkill')[1].split("\n")[0]


def test_the_helper_programs_of_the_full_install_job_are_not_written_into_the_checkout():
    """A test of the checkout (every file of code has its license header) once found them there."""
    job = workflow_text().split("  windows-full-install:")[1]
    for name in ("browser_smoke.py", "build_site.py", "arabic_smoke.py"):
        assert f"Set-Content (Join-Path $env:RUNNER_TEMP '{name}')" in job, name
        assert f"Set-Content {name}" not in job


def test_no_job_can_hold_up_the_run_for_ever():
    yaml = pytest.importorskip("yaml")
    for name, job in yaml.safe_load(workflow_text())["jobs"].items():
        assert isinstance(job.get("timeout-minutes"), int), f"{name} has no timeout-minutes"
