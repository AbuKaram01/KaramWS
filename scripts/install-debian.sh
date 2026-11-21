#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# One-command installer for KaramWS on Debian/Ubuntu-based systems, from a git checkout: it installs into the
# checkout (.venv and browsers/) and into your own $HOME. Prefer a real package? See packaging/build.sh.
# Run from anywhere:  ./scripts/install-debian.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

APP_ID="io.github.AbuKaram01.KaramWS"
REQUIRED_PYTHON="3.10"

info() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
ok()   { printf '\033[1;32m✓\033[0m %s\n' "$1"; }
fail() { printf '\033[1;31m✗ %s\033[0m\n' "$1" >&2; exit 1; }

if ! command -v apt >/dev/null 2>&1; then
    fail "This script is for Debian/Ubuntu-based systems (needs apt). Not found on this machine — on Arch-based systems use scripts/install-arch.sh."
fi

if [ "$EUID" -eq 0 ]; then
    fail "Don't run this as root — it installs into your own \$HOME. Run it as your normal user; it will ask for sudo only for the system packages."
fi

info "Installing system packages (GTK4, libadwaita, Python bindings)..."
sudo apt update -qq
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 librsvg2-common python3-venv python3-pip
ok "System packages installed."

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [ "$(printf '%s\n' "$REQUIRED_PYTHON" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON" ]; then
    fail "Python $REQUIRED_PYTHON+ is required — found $PYTHON_VERSION."
fi
ok "Python $PYTHON_VERSION OK."

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
# which is where KaramWS looks for it, so nothing else has to be configured. The system libraries it needs are
# installed by Playwright's own command (it asks for sudo).
info "Installing the browser for JavaScript pages (Chromium)..."
sudo .venv/bin/python -m playwright install-deps chromium
PLAYWRIGHT_BROWSERS_PATH="$PROJECT_ROOT/browsers" .venv/bin/python -m playwright install chromium
ok "Chromium installed."

info "Installing the desktop launcher and app icon for your user..."
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor
# GIO refuses to even register a desktop entry whose Exec command can't be
# resolved — and "karamws-gui" only exists inside .venv/bin, not on the
# system PATH, so a plain copy of the template silently fails to appear
# anywhere (search, app grid, gtk-launch — all of it). The absolute path
# always resolves regardless of PATH.
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
