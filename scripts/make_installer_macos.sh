#!/usr/bin/env bash
# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
#
# Build the Sequence RV macOS installer (SequenceRV-<version>.dmg).
# Runs on macOS only (uses PlistBuddy, codesign, hdiutil).
#
#   scripts/make_installer_macos.sh [path/to/RV.app]
#
# The .app defaults to the first *.app under the upstream stage directory.
# Steps: copy the app, rebrand it (name + Sequence icon), ad-hoc sign, and
# wrap it in a compressed DMG under dist/.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "$ROOT/VERSION")"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "error: this script must run on macOS" >&2
    exit 1
fi

APP_SRC="${1:-}"
if [ -z "$APP_SRC" ]; then
    APP_SRC="$(find "$ROOT/_external/OpenRV/_build/stage" -maxdepth 3 -type d -name '*.app' 2>/dev/null | head -n1 || true)"
fi
if [ -z "$APP_SRC" ] || [ ! -d "$APP_SRC" ]; then
    echo "error: no .app found — pass the built RV.app path explicitly" >&2
    exit 1
fi

ICNS="$ROOT/branding/icon.icns"
if [ ! -f "$ICNS" ]; then
    echo "error: branding/icon.icns missing — run scripts/make_brand_assets.py" >&2
    exit 1
fi

WORK="$(mktemp -d /tmp/sequence-rv-dmg.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT
APP="$WORK/Sequence RV.app"

echo "Staging $APP_SRC -> $APP"
cp -R "$APP_SRC" "$APP"

PLIST="$APP/Contents/Info.plist"
PB=/usr/libexec/PlistBuddy

# Replace the bundle icon: honor the existing CFBundleIconFile name so no
# plist/rc references break, falling back to a conventional name.
ICON_NAME="$($PB -c 'Print :CFBundleIconFile' "$PLIST" 2>/dev/null || echo 'RV.icns')"
case "$ICON_NAME" in *.icns) : ;; *) ICON_NAME="$ICON_NAME.icns" ;; esac
cp "$ICNS" "$APP/Contents/Resources/$ICON_NAME"

$PB -c 'Set :CFBundleName "Sequence RV"' "$PLIST" 2>/dev/null \
    || $PB -c 'Add :CFBundleName string "Sequence RV"' "$PLIST"
$PB -c 'Set :CFBundleDisplayName "Sequence RV"' "$PLIST" 2>/dev/null \
    || $PB -c 'Add :CFBundleDisplayName string "Sequence RV"' "$PLIST"

# Re-sign after modification. Ad-hoc by default; set SEQ_CODESIGN_ID to a
# Developer ID for distribution outside machines you manage (Gatekeeper will
# quarantine unsigned/ad-hoc apps downloaded from the internet — for studio
# deployment over a file share or MDM this is typically fine).
IDENTITY="${SEQ_CODESIGN_ID:--}"
echo "Codesigning with identity: $IDENTITY"

if [ "$IDENTITY" = "-" ]; then
    # Ad-hoc: no runtime hardening (can't be notarized, and doesn't need to be).
    codesign --force --deep --sign "-" "$APP"
else
    # Developer ID path — sign for notarization. This needs, in order:
    #   --options runtime : the hardened runtime notarization requires
    #   --timestamp       : a secure Apple timestamp (notarization rejects
    #                       signatures without one)
    #   --entitlements    : the hardened-runtime carve-outs RV needs to load
    #                       its unsigned plugins and run embedded CPython
    # --deep is deprecated and signs nested code inside-out unreliably, so we
    # sign every nested Mach-O bottom-up ourselves, then the outer bundle last.
    ENTITLEMENTS="$ROOT/branding/entitlements.plist"
    if [ ! -f "$ENTITLEMENTS" ]; then
        echo "error: $ENTITLEMENTS missing (needed for hardened-runtime signing)" >&2
        exit 1
    fi
    SIGN=(codesign --force --timestamp --options runtime \
                   --entitlements "$ENTITLEMENTS" --sign "$IDENTITY")

    echo "Signing nested code (frameworks, dylibs, helper binaries) bottom-up…"
    # Frameworks and loadable bundles first.
    while IFS= read -r -d '' item; do
        "${SIGN[@]}" "$item"
    done < <(find "$APP/Contents" \( -name '*.framework' -o -name '*.dylib' \
                    -o -name '*.so' -o -name '*.bundle' \) -print0)
    # Any remaining Mach-O executables (helper tools, python, rvio, etc.).
    while IFS= read -r -d '' f; do
        if file "$f" | grep -q 'Mach-O'; then "${SIGN[@]}" "$f" || true; fi
    done < <(find "$APP/Contents/MacOS" -type f -print0)
    # Outer bundle last so its seal covers everything inside.
    "${SIGN[@]}" "$APP"

    echo "Verifying signature…"
    codesign --verify --deep --strict --verbose=2 "$APP"
fi

mkdir -p "$ROOT/dist"
DMG="$ROOT/dist/SequenceRV-$VERSION.dmg"
rm -f "$DMG"

# Standard drag-to-Applications layout.
ln -s /Applications "$WORK/Applications"
hdiutil create -volname "Sequence RV" -srcfolder "$WORK" -ov -format UDZO "$DMG"

echo
echo "Installer written to $DMG"
