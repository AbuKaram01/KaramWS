#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Builds, into packaging/dist/, every package format this machine has the tools for:
#   karamws_<ver>_amd64.deb          (Debian/Ubuntu)
#   karamws-<ver>-1.x86_64.rpm       (Fedora/RHEL family)
#   karamws-<ver>-1-x86_64.pkg.tar.* (Arch Linux, built by packaging/build-arch.sh)
#
# These packages ship NO Python dependencies and no browser: they are small. On install, their
# postinst/%post/.install script runs /usr/lib/karamws/setup-venv, which creates a venv at
# /opt/karamws/venv, runs `pip install` there and downloads Chromium (for Playwright) into
# /opt/karamws/browsers. That needs internet access once, at install time.
#
# Tools needed on the machine that RUNS this script (not on the machine installing the
# packages) - at least one set:
#   .deb  -> dpkg-deb  (Debian/Ubuntu: dpkg-dev)
#   .rpm  -> rpmbuild  (the `rpm` package; `rpm-build` on Fedora)
#   Arch  -> makepkg   (Arch Linux; must NOT be run as root - makepkg refuses)
# Formats whose tool is missing are skipped, with a note at the end.
# Extra makepkg options can be passed with MAKEPKG_FLAGS (e.g. MAKEPKG_FLAGS=-s to install
# missing dependencies with pacman first).

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$PROJECT_ROOT/packaging/work"
OUT_DIR="$PROJECT_ROOT/packaging/dist"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$PROJECT_ROOT/src/karamws/__init__.py")"
APP_ID="$(sed -n 's/^APP_ID = "\(.*\)"/\1/p' "$PROJECT_ROOT/src/karamws/__init__.py")"
MAINTAINER="AbuKaram01 <abukaram01@proton.me>"
SUMMARY="Karam Web Scraper - save the articles of a page, a section or a whole website as Markdown"

[ -n "$VERSION" ] || { echo "Could not read the version from src/karamws/__init__.py." >&2; exit 1; }
[ -n "$APP_ID" ] || { echo "Could not read APP_ID from src/karamws/__init__.py." >&2; exit 1; }

info() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
ok()   { printf '\033[1;32m✓\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m!\033[0m %s\n' "$1"; }

HAVE_DEB=0; HAVE_RPM=0; HAVE_ARCH=0
command -v dpkg-deb >/dev/null 2>&1 && HAVE_DEB=1
command -v rpmbuild >/dev/null 2>&1 && HAVE_RPM=1
if command -v makepkg >/dev/null 2>&1; then
    if [ "$(id -u)" -eq 0 ]; then
        warn "makepkg is installed but refuses to run as root - run build.sh as a normal user to build the Arch package."
    else
        HAVE_ARCH=1
    fi
fi
if [ $((HAVE_DEB + HAVE_RPM + HAVE_ARCH)) -eq 0 ]; then
    echo "No packaging tool found. Install at least one of: dpkg-deb (dpkg-dev), rpmbuild (rpm / rpm-build)," >&2
    echo "or run on Arch Linux as a normal user with makepkg available." >&2
    exit 1
fi

# Clean only what this script produces, so a package built by build-arch.sh survives.
rm -rf "$WORK_DIR/payload" "$WORK_DIR/deb-root" "$WORK_DIR/rpmbuild"
mkdir -p "$WORK_DIR" "$OUT_DIR"
rm -f "$OUT_DIR"/karamws_*_amd64.deb "$OUT_DIR"/karamws-*.x86_64.rpm

# ── The files every format installs ──────────────────────────────────────────
payload="$WORK_DIR/payload"
build_payload() {
    # pip builds from this folder, so everything pyproject.toml refers to must be here.
    mkdir -p "$payload/opt/karamws/src"
    cp -r "$PROJECT_ROOT/src" "$PROJECT_ROOT/pyproject.toml" "$PROJECT_ROOT/README.md" "$PROJECT_ROOT/LICENSE" \
        "$payload/opt/karamws/src/"
    find "$payload/opt/karamws/src" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

    mkdir -p "$payload/usr/bin"
    # A package always installs to the same place, so these paths are always right.
    printf '#!/bin/sh\nexec /opt/karamws/venv/bin/python3 -m karamws.gui "$@"\n' > "$payload/usr/bin/karamws-gui"
    printf '#!/bin/sh\nexec /opt/karamws/venv/bin/python3 -m karamws "$@"\n' > "$payload/usr/bin/karamws"
    chmod 755 "$payload/usr/bin/karamws-gui" "$payload/usr/bin/karamws"

    mkdir -p "$payload/usr/share/applications" "$payload/usr/share/icons" "$payload/usr/share/licenses/karamws"
    cp "$PROJECT_ROOT/data/${APP_ID}.desktop" "$payload/usr/share/applications/"
    cp -r "$PROJECT_ROOT/data/icons/hicolor" "$payload/usr/share/icons/"
    cp "$PROJECT_ROOT/LICENSE" "$payload/usr/share/licenses/karamws/LICENSE"

    mkdir -p "$payload/usr/lib/karamws"
    install -m 755 "$PROJECT_ROOT/packaging/linux/karamws-setup-venv" "$payload/usr/lib/karamws/setup-venv"
}

# What the install scripts do: set the environment up, and keep going (with a note) if that fails, so a missing
# internet connection does not leave the package half-installed.
postinst_body=$(cat << 'POSTINST'
if ! /usr/lib/karamws/setup-venv; then
    echo "KaramWS: WARNING: its Python environment could not be set up."
    echo "  Fix the cause (internet connection?) and run: sudo /usr/lib/karamws/setup-venv"
fi
POSTINST
)

build_payload

# ==== .deb ==================================================================
if [ "$HAVE_DEB" -eq 1 ]; then
    info "Building karamws_${VERSION}_amd64.deb..."
    deb_root="$WORK_DIR/deb-root"
    cp -r "$payload" "$deb_root"
    mkdir -p "$deb_root/DEBIAN" "$deb_root/usr/share/doc/karamws"
    cp "$PROJECT_ROOT/LICENSE" "$deb_root/usr/share/doc/karamws/copyright"

    # The libraries Chromium needs (Playwright's own list for Ubuntu/Debian). Ubuntu 24.04 and Debian 13 renamed some
    # of them with a t64 suffix: either name will do.
    chromium_libs="libasound2t64 | libasound2, libatk-bridge2.0-0t64 | libatk-bridge2.0-0, libatk1.0-0t64 | libatk1.0-0, \
libatspi2.0-0t64 | libatspi2.0-0, libcairo2, libcups2t64 | libcups2, libdbus-1-3, libdrm2, libgbm1, \
libglib2.0-0t64 | libglib2.0-0, libnspr4, libnss3, libpango-1.0-0, libx11-6, libxcb1, libxcomposite1, libxdamage1, \
libxext6, libxfixes3, libxkbcommon0, libxrandr2"

    cat > "$deb_root/DEBIAN/control" << CONTROL
Package: karamws
Version: $VERSION
Section: web
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.10), python3-venv, python3-pip, python3-gi, python3-gi-cairo, gir1.2-gtk-4.0, gir1.2-adw-1 (>= 1.5), librsvg2-common, $chromium_libs
Maintainer: $MAINTAINER
Homepage: https://github.com/AbuKaram01/KaramWS
Description: $SUMMARY
 Give it a link to an article, a section or a whole website and it saves the
 articles as Markdown files. Downloads its Python libraries and a Chromium
 browser (for pages that need JavaScript) on first install; it needs internet
 access then, and not afterwards to run it.
CONTROL

    {
        printf '#!/bin/sh\nset -e\nif [ "$1" = "configure" ]; then\n%s\nfi\nexit 0\n' "$postinst_body"
    } > "$deb_root/DEBIAN/postinst"
    cat > "$deb_root/DEBIAN/postrm" << 'POSTRM'
#!/bin/sh
set -e
if [ "$1" = "purge" ] || [ "$1" = "remove" ]; then
    # Not only the package's own files: pip leaves build files in src/, and the venv and the browser are not in
    # the package at all.
    rm -rf /opt/karamws
fi
exit 0
POSTRM
    chmod 755 "$deb_root/DEBIAN/postinst" "$deb_root/DEBIAN/postrm"

    dpkg-deb --build --root-owner-group "$deb_root" "$OUT_DIR/karamws_${VERSION}_amd64.deb" >/dev/null
    ok "karamws_${VERSION}_amd64.deb"
fi

# ==== .rpm ==================================================================
if [ "$HAVE_RPM" -eq 1 ]; then
    info "Building karamws-${VERSION}-1.x86_64.rpm..."
    rpm_topdir="$WORK_DIR/rpmbuild"
    mkdir -p "$rpm_topdir"/{BUILD,RPMS,SOURCES,SPECS,SRPMS,BUILDROOT}

    spec_file="$rpm_topdir/SPECS/karamws.spec"
    cat > "$spec_file" << SPEC
Name: karamws
Version: $VERSION
Release: 1
Summary: $SUMMARY
License: AGPL-3.0-or-later
URL: https://github.com/AbuKaram01/KaramWS
BuildArch: x86_64
# The second line is what the Chromium that Playwright downloads needs from the system.
Requires: python3 >= 3.10, python3-pip, python3-gobject, gtk4, libadwaita >= 1.5, librsvg2
Requires: nss, nspr, alsa-lib, atk, at-spi2-atk, at-spi2-core, cups-libs, libdrm, mesa-libgbm, libXcomposite, libXdamage, libXfixes, libXrandr, libxkbcommon, pango, cairo

%description
Give it a link to an article, a section or a whole website and it saves the
articles as Markdown files. Downloads its Python libraries and a Chromium
browser (for pages that need JavaScript) on first install; it needs internet
access then, and not afterwards to run it.

%install
mkdir -p %{buildroot}
cp -a $payload/. %{buildroot}/

%files
/opt/karamws
/usr/bin/karamws
/usr/bin/karamws-gui
/usr/lib/karamws
/usr/share/applications/*.desktop
/usr/share/icons/hicolor
/usr/share/licenses/karamws

%post
$postinst_body

%postun
if [ "\$1" = "0" ]; then
    rm -rf /opt/karamws
fi

%clean
rm -rf %{buildroot}
SPEC

    rpmbuild --define "_topdir $rpm_topdir" -bb "$spec_file" >/dev/null 2>&1 || \
        rpmbuild --define "_topdir $rpm_topdir" -bb "$spec_file"
    find "$rpm_topdir/RPMS" -name "*.rpm" -exec cp {} "$OUT_DIR/" \;
    ok "karamws-${VERSION}-1.x86_64.rpm"
fi

# ==== Arch (.pkg.tar.*) =====================================================
# build-arch.sh makes the source tarball from this checkout and runs makepkg, leaving the result in packaging/dist.
if [ "$HAVE_ARCH" -eq 1 ]; then
    info "Building karamws for Arch (packaging/build-arch.sh)..."
    # shellcheck disable=SC2086  # MAKEPKG_FLAGS is meant to word-split
    "$PROJECT_ROOT/packaging/build-arch.sh" --noconfirm ${MAKEPKG_FLAGS:-}
    for built in "$OUT_DIR"/karamws*.pkg.tar.*; do ok "$(basename "$built")"; done
fi

echo
ok "Packages built in: $OUT_DIR"
ls -la "$OUT_DIR"
[ "$HAVE_DEB" -eq 1 ]  || warn "Skipped .deb  (dpkg-deb not found)"
[ "$HAVE_RPM" -eq 1 ]  || warn "Skipped .rpm  (rpmbuild not found)"
[ "$HAVE_ARCH" -eq 1 ] || warn "Skipped Arch package (makepkg not found, or running as root)"
exit 0
