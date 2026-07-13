#!/usr/bin/env bash
# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
#
# Bundle the studio kit into a built OpenRV distribution:
#   * copies dist/*.rvpkg into the distribution's plugins/Packages directory
#   * registers them in the 'rvinstall' auto-install list when present
#   * copies the seqrv/seqrvio launchers next to the rv binary
#
#   scripts/bundle_release.sh [stage_dir]
#
# stage_dir defaults to _external/OpenRV/_build/stage/app (upstream layout).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="${1:-$ROOT/_external/OpenRV/_build/stage/app}"

if [ ! -d "$STAGE" ]; then
    echo "error: stage directory not found: $STAGE" >&2
    echo "       pass the built distribution root explicitly, e.g." >&2
    echo "       scripts/bundle_release.sh /path/to/OpenRV-install" >&2
    exit 1
fi

shopt -s nullglob
PKGS=("$ROOT"/dist/*.rvpkg)
shopt -u nullglob
if [ ${#PKGS[@]} -eq 0 ]; then
    echo "error: no .rvpkg files in dist/ — run 'make packages' first" >&2
    exit 1
fi

# Locate the packages dir inside the distribution (layout differs slightly
# between platforms: plugins/Packages on Linux/Windows, inside the .app on mac).
PKG_DIR="$(find "$STAGE" -maxdepth 5 -type d -name Packages -path '*lugins*' | head -n1 || true)"
if [ -z "$PKG_DIR" ]; then
    PKG_DIR="$(find "$STAGE" -maxdepth 6 -type d -name Packages | head -n1 || true)"
fi
if [ -z "$PKG_DIR" ]; then
    echo "error: could not find a plugins/Packages directory under $STAGE" >&2
    exit 1
fi

echo "Installing ${#PKGS[@]} package(s) into $PKG_DIR"
cp -v "${PKGS[@]}" "$PKG_DIR/"

# rvinstall lists package files the app installs into its own area on first
# run. Append ours if the mechanism exists in this distribution.
RVINSTALL="$PKG_DIR/rvinstall"
if [ -f "$RVINSTALL" ]; then
    for pkg in "${PKGS[@]}"; do
        base="$(basename "$pkg")"
        grep -qxF "$base" "$RVINSTALL" || echo "$base" >> "$RVINSTALL"
    done
    echo "Updated $(basename "$RVINSTALL") auto-install list"
else
    echo "note: no rvinstall list found; packages are in place but artists may"
    echo "      need to enable them once via RV Preferences > Packages, or you"
    echo "      can pre-install into the image with: rvpkg -install -add <support> ${PKGS[*]}"
fi

# Kit runtime data (studio configs, placeholder OCIO config, and the OCIO
# resolver the launchers call) lives in <dist>/sequence — the launchers look
# there first when deciding SEQ_KIT_ROOT.
KIT_DEST="$STAGE/sequence"
mkdir -p "$KIT_DEST/configs" "$KIT_DEST/ocio" "$KIT_DEST/scripts"
cp -v "$ROOT/configs/ocio_rules.json" "$KIT_DEST/configs/"
cp -v "$ROOT/ocio/config.ocio" "$KIT_DEST/ocio/"
cp -v "$ROOT/scripts/resolve_ocio.py" "$KIT_DEST/scripts/"
cp -v "$ROOT/packages/sequence_ocio/sequence_ocio_core.py" "$KIT_DEST/scripts/"

# Launchers next to the rv binary when we can find it.
RV_BIN="$(find "$STAGE" -maxdepth 4 -type f \( -name rv -o -name rv.exe \) | head -n1 || true)"
if [ -n "$RV_BIN" ]; then
    RV_BIN_DIR="$(dirname "$RV_BIN")"
    cp -v "$ROOT/bin/seqrv" "$ROOT/bin/seqrvio" \
          "$ROOT/bin/seqrv.cmd" "$ROOT/bin/seqrvio.cmd" "$RV_BIN_DIR/"
    chmod +x "$RV_BIN_DIR/seqrv" "$RV_BIN_DIR/seqrvio"
fi

echo
echo "Bundle complete. Distribution root: $STAGE"
echo "Archive it for deployment, e.g.:"
echo "  tar -C \"$(dirname "$STAGE")\" -czf sequence-rv-\$(cat "$ROOT/VERSION").tar.gz \"$(basename "$STAGE")\""
