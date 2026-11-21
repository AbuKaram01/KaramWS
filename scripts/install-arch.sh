#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# One-command installer for KaramWS on Arch-based systems (Arch, Manjaro, EndeavourOS...),
# from a git checkout — installs into the checkout (.venv and browsers/) and your own $HOME,
# like scripts/install-debian.sh.
# Run from anywhere:  ./scripts/install-arch.sh
#
# Prefer a real package? Build one with packaging/build-arch.sh (see the README).

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

APP_ID="io.github.AbuKaram01.KaramWS"
REQUIRED_PYTHON="3.10"

info() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
ok()   { printf '\033[1;32m✓\033[0m %s\n' "$1"; }
fail() { printf '\033[1;31m✗ %s\033[0m\n' "$1" >&2; exit 1; }

if ! command -v pacman >/dev/null 2>&1; then
    fail "This script is for Arch-based systems (needs pacman). Not found on this machine — on Debian/Ubuntu use scripts/install-debian.sh."
fi

if [ "$EUID" -eq 0 ]; then
    fail "Don't run this as root — it installs into your own \$HOME. Run it as your normal user; it will ask for sudo only for the system packages."
fi

# The second line is what the Chromium that Playwright downloads needs from the system.
PACKAGES=(
    python python-pip python-gobject gtk4 libadwaita librsvg adwaita-icon-theme
    nss nspr alsa-lib at-spi2-core libcups libdrm mesa libxcomposite libxdamage libxfixes libxrandr libxkbcommon pango cairo
)

info "Installing system packages (GTK4, libadwaita, Python bindings, what Chromium needs)..."
# --needed: skip what is already installed (and don't reinstall it).
sudo pacman -S --needed --noconfirm "${PACKAGES[@]}"
ok "System packages installed."

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [ "$(printf '%s\n' "$REQUIRED_PYTHON" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON" ]; then
    fail "Python $REQUIRED_PYTHON+ is required — found $PYTHON_VERSION."
fi
ok "Python $PYTHON_VERSION OK."

# Arch is a rolling release: if Python has moved to a new minor version since .venv was
# created, that .venv no longer works — start it over rather than reuse it.
if [ -d .venv ]; then
    VENV_VERSION="$(sed -n 's/^version[[:space:]]*=[[:space:]]*\([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' .venv/pyvenv.cfg 2>/dev/null | head -n 1)"
    if [ "$VENV_VERSION" != "$PYTHON_VERSION" ]; then
        info "The existing .venv was made with Python ${VENV_VERSION:-?}, the system now has $PYTHON_VERSION — recreating it."
        rm -rf .venv
    fi
fi

if [ ! -d .venv ]; then
    info "Creating virtual environment (.venv)..."
    python3 -m venv --system-site-packages .venv
    ok "Virtual environment created."
else
    info "Reusing existing .venv"
fi

info "Installing Python dependencies..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -e . -q
ok "Python dependencies installed."

# Chromium, for the pages that only show their content after JavaScript runs. It goes into browsers/ beside .venv,
# which is where KaramWS looks for it, so nothing else has to be configured.
info "Installing the browser for JavaScript pages (Chromium)..."
PLAYWRIGHT_BROWSERS_PATH="$PROJECT_ROOT/browsers" .venv/bin/python -m playwright install chromium
ok "Chromium installed."

info "Installing the desktop launcher and app icon for your user..."
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor
# The launcher's Exec needs an absolute path: "karamws-gui" only exists inside .venv/bin,
# not on the system PATH, and a desktop entry whose Exec can't be resolved is silently
# not registered at all.
sed "s|^Exec=karamws-gui|Exec=${PROJECT_ROOT}/.venv/bin/karamws-gui|" \
    "data/${APP_ID}.desktop" > ~/.local/share/applications/"${APP_ID}.desktop"
cp -r data/icons/hicolor/* ~/.local/share/icons/hicolor/
gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true
ok "Desktop launcher and icon installed."

echo
ok "KaramWS is installed."
echo
echo "  Run it with:"
echo "    ${PROJECT_ROOT}/.venv/bin/karamws-gui"
echo
echo "  Or activate the virtual environment first:"
echo "    source ${PROJECT_ROOT}/.venv/bin/activate"
echo "    karamws-gui"
echo
echo "  It should also now appear in your applications menu as \"KaramWS\"."
echo "  The command line works the same way:  karamws --help"
echo
echo "Note: after an Arch update moves Python to a new minor version, re-run this"
echo "script: it rebuilds .venv for the new Python."
