# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Checks on the files of the packages: the names and versions agree everywhere, the scripts are sound, and a
real .deb built from the project holds what the install scripts expect."""

import re
import shutil
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from packaging_support import APP_ID, ARCH, ROOT, WINDOWS, make_executable, needs_bash

import karamws

PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- one name, one version ---

def test_the_version_is_the_same_everywhere():
    version = karamws.__version__
    assert PYPROJECT["project"]["version"] == version
    assert re.search(rf"^pkgver={re.escape(version)}$", read(ARCH / "PKGBUILD"), re.M)
    assert f'#define AppVersion "{version}"' in read(WINDOWS / "karamws.iss")


def test_the_app_id_names_the_desktop_file_the_icon_and_the_windows_installer():
    assert karamws.APP_ID == APP_ID == "io.github.AbuKaram01.KaramWS"
    assert (ROOT / "data" / f"{APP_ID}.desktop").is_file()
    assert (ROOT / "data" / "icons" / "hicolor" / "scalable" / "apps" / f"{APP_ID}.svg").is_file()
    assert f'#define AppId "{APP_ID}"' in read(WINDOWS / "karamws.iss")


def test_the_project_is_agpl_and_says_who_wrote_it():
    project = PYPROJECT["project"]
    assert project["license"] == "AGPL-3.0-or-later"
    assert project["authors"] == [{"name": "AbuKaram01", "email": "abukaram01@proton.me"}]
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in read(ROOT / "LICENSE")
    assert "Maintainer: AbuKaram01 <abukaram01@proton.me>" in read(ARCH / "PKGBUILD")


def test_playwright_is_a_dependency_so_every_installer_carries_it():
    dependencies = " ".join(PYPROJECT["project"]["dependencies"])
    for needed in ("trafilatura", "httpx", "playwright"):
        assert needed in dependencies
    assert "playwright" in read(ROOT / "requirements.txt")


# --- the desktop entry, the icon and the entry points ---

def test_the_desktop_entry_launches_the_graphical_program_with_the_app_icon():
    entry = dict(
        line.split("=", 1) for line in read(ROOT / "data" / f"{APP_ID}.desktop").splitlines() if "=" in line
    )
    assert entry["Exec"] in PYPROJECT["project"]["scripts"]
    assert entry["Icon"] == APP_ID and entry["Name"] == "KaramWS" and entry["Type"] == "Application"
    assert entry["Terminal"] == "false"


def test_the_scripts_of_the_project_point_at_functions_that_exist():
    from importlib import import_module

    for command, target in PYPROJECT["project"]["scripts"].items():
        module_name, function = target.split(":")
        if ".gui." in module_name:
            pytest.importorskip("gi")  # The window needs GTK to be imported.
        assert callable(getattr(import_module(module_name), function)), command


def test_the_icon_is_a_square_svg_and_the_windows_icon_has_every_size():
    svg = ROOT / "data" / "icons" / "hicolor" / "scalable" / "apps" / f"{APP_ID}.svg"
    root = ET.fromstring(svg.read_text(encoding="utf-8"))
    assert root.tag.endswith("svg") and root.get("viewBox") == "0 0 512 512"
    icon = (ROOT / "data" / "windows" / "karamws.ico").read_bytes()
    assert icon[:4] == b"\x00\x00\x01\x00"
    sizes = {(icon[6 + 16 * i] or 256) for i in range(int.from_bytes(icon[4:6], "little"))}
    assert sizes == {16, 24, 32, 48, 64, 128, 256}


# --- the license header on every file that is code ---

def test_every_file_of_code_carries_the_license_header():
    suffixes = {".py", ".sh", ".ps1", ".iss", ".yml"}
    names = {"PKGBUILD", "karamws.install", "karamws-setup-venv", "karamws.hook"}
    missing = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        generated = {".venv", "work", "dist", "__pycache__", ".git"}
        if not path.is_file() or any(part in generated for part in relative.parts):
            continue
        if path.suffix in suffixes or path.name in names:
            if "SPDX-License-Identifier: AGPL-3.0-or-later" not in read(path):
                missing.append(str(relative))
    assert not missing, missing


# --- the Linux scripts ---

SHELL_SCRIPTS = [
    ROOT / "packaging" / "build.sh",
    ROOT / "packaging" / "build-arch.sh",
    ROOT / "packaging" / "linux" / "karamws-setup-venv",
    ROOT / "scripts" / "install-debian.sh",
    ROOT / "scripts" / "install-arch.sh",
]


@needs_bash
@pytest.mark.parametrize("script", SHELL_SCRIPTS, ids=lambda path: path.name)
def test_every_shell_script_parses(script):
    result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_the_arch_package_files_agree_with_each_other():
    pkgbuild = read(ARCH / "PKGBUILD")
    assert "install=karamws.install" in pkgbuild and (ARCH / "karamws.install").is_file()
    # Everything the PKGBUILD installs from the source tree exists in it.
    for relative in re.findall(r'"\$root/([^"]+)"', pkgbuild):
        if "$" in relative or relative.endswith("hicolor"):
            continue
        assert (ROOT / relative.replace("$app_id", APP_ID)).exists(), relative
    # The hook runs the very script that the package installs.
    assert "/usr/lib/karamws/setup-venv" in read(ARCH / "karamws.hook")
    assert "/usr/lib/karamws/setup-venv" in pkgbuild and "/usr/lib/karamws/setup-venv" in read(ARCH / "karamws.install")
    # The pip build reads the readme and the license, so they travel with the sources.
    assert '"$root/README.md" "$root/LICENSE"' in pkgbuild


def test_every_linux_package_removes_everything_under_opt_when_it_is_removed():
    for text in (read(ROOT / "packaging" / "build.sh"), read(ARCH / "karamws.install")):
        assert text.count("rm -rf /opt/karamws") >= 1
    # ... and sets the environment up, warning (not failing) when the network is not there.
    assert "setup-venv" in read(ARCH / "karamws.install")
    assert "could not be set up" in read(ROOT / "packaging" / "build.sh")


@needs_bash
def test_the_setup_script_leaves_an_environment_of_the_same_python_alone(tmp_path):
    """The pacman hook runs it after every Python upgrade, most of which are not a new minor version."""
    app = tmp_path / "app"
    (app / "venv").mkdir(parents=True)
    minor = f"{sys.version_info.major}.{sys.version_info.minor}"
    (app / "venv" / "pyvenv.cfg").write_text(f"home = /usr/bin\nversion = {minor}.1\n", encoding="utf-8")
    result = subprocess.run(
        [str(ROOT / "packaging" / "linux" / "karamws-setup-venv"), "--if-python-changed"],
        env={"KARAMWS_APP_DIR": str(app), "KARAMWS_PYTHON": sys.executable, "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0 and result.stdout == "", result.stdout + result.stderr
    assert (app / "venv" / "pyvenv.cfg").is_file()  # Untouched.


@needs_bash
def test_the_setup_script_does_nothing_when_there_is_no_environment_yet(tmp_path):
    result = subprocess.run(
        [str(ROOT / "packaging" / "linux" / "karamws-setup-venv"), "--if-python-changed"],
        env={"KARAMWS_APP_DIR": str(tmp_path / "app"), "KARAMWS_PYTHON": sys.executable, "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0 and not (tmp_path / "app").exists()


@needs_bash
def test_the_setup_script_installs_the_app_and_still_succeeds_when_chromium_cannot_be_downloaded(tmp_path):
    """The package must not be left half-installed because the browser download failed: the script tells the user
    how to try again and ends well. Stand-ins for the interpreter and pip keep this off the network."""
    app = tmp_path / "app"
    (app / "src").mkdir(parents=True)
    log = tmp_path / "calls.log"
    fake_python = make_executable(
        tmp_path / "python3",
        "#!/bin/sh\n"
        f'echo "python3 $*" >> "{log}"\n'
        'case "$*" in\n'
        '  *"import sys"*) echo "3.12" ;;\n'
        '  "-m venv"*) mkdir -p "$4/bin"; cp "$0" "$4/bin/python3"; printf "version = 3.12.3\\n" > "$4/pyvenv.cfg"; '
        f'printf "#!/bin/sh\\necho pip \\"\\$*\\" >> {log}\\n" > "$4/bin/pip"; chmod +x "$4/bin/pip" ;;\n'
        '  "-m playwright install chromium") echo "download failed" >&2; exit 1 ;;\n'
        "esac\n",
    )
    result = subprocess.run(
        [str(ROOT / "packaging" / "linux" / "karamws-setup-venv")],
        env={"KARAMWS_APP_DIR": str(app), "KARAMWS_PYTHON": str(fake_python), "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    calls = log.read_text(encoding="utf-8")
    assert f"pip install --quiet {app}/src" in calls  # The app went into the environment ...
    assert "-m playwright install chromium" in calls  # ... and the browser was attempted, beside it.
    assert "Chromium could not be downloaded" in result.stdout and "sudo /usr/lib/karamws/setup-venv" in result.stdout


# --- a real .deb ---

@pytest.mark.skipif(shutil.which("dpkg-deb") is None, reason="needs dpkg-deb")
@needs_bash
def test_the_deb_built_from_the_project_holds_what_the_install_scripts_expect(tmp_path):
    copy = tmp_path / "KaramWS"
    left_out = shutil.ignore_patterns(".venv", "__pycache__", "work", "dist", ".git", "*.egg-info")
    shutil.copytree(ROOT, copy, ignore=left_out)
    build_script = str(copy / "packaging" / "build.sh")
    build = subprocess.run(["bash", build_script], capture_output=True, text=True, check=False)
    assert build.returncode == 0, build.stdout + build.stderr
    deb = next((copy / "packaging" / "dist").glob("karamws_*_amd64.deb"))
    assert karamws.__version__ in deb.name

    listing = subprocess.run(["dpkg-deb", "-c", str(deb)], capture_output=True, text=True, check=True).stdout
    for expected in (
        "./usr/bin/karamws-gui",
        "./usr/bin/karamws",
        "./usr/lib/karamws/setup-venv",
        f"./usr/share/applications/{APP_ID}.desktop",
        f"./usr/share/icons/hicolor/scalable/apps/{APP_ID}.svg",
        "./usr/share/doc/karamws/copyright",
        "./opt/karamws/src/pyproject.toml",
        "./opt/karamws/src/README.md",  # pip builds from here, so what pyproject.toml refers to must be here
        "./opt/karamws/src/LICENSE",
        "./opt/karamws/src/src/karamws/__init__.py",
    ):
        assert expected in listing, expected

    control = subprocess.run(["dpkg-deb", "-f", str(deb)], capture_output=True, text=True, check=True).stdout
    depends = next(line for line in control.splitlines() if line.startswith("Depends:"))
    for needed in ("python3-gi", "gir1.2-adw-1 (>= 1.5)", "libnss3", "libasound2t64 | libasound2"):
        assert needed in depends, needed
    assert "Maintainer: AbuKaram01 <abukaram01@proton.me>" in control

    scripts = tmp_path / "control"
    subprocess.run(["dpkg-deb", "-e", str(deb), str(scripts)], check=True)
    postinst = read(scripts / "postinst")
    assert "/usr/lib/karamws/setup-venv" in postinst and postinst.startswith("#!/bin/sh")
    assert "rm -rf /opt/karamws" in read(scripts / "postrm")
    launcher = subprocess.run(
        ["dpkg-deb", "--fsys-tarfile", str(deb)], capture_output=True, check=True,
    ).stdout
    assert b"exec /opt/karamws/venv/bin/python3 -m karamws.gui" in launcher
