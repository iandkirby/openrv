#!/usr/bin/env bash
# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
#
# Install the built dist/*.rvpkg files into an RV support directory using the
# rvpkg tool that ships with RV/OpenRV.
#
#   scripts/install_packages.sh [support_dir]
#
# support_dir defaults to ~/.rv (RV's per-user support directory).
# rvpkg is located via $SEQ_RVPKG, then $PATH, then $RV_HOME/bin.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUPPORT="${1:-$HOME/.rv}"

shopt -s nullglob
PKGS=("$ROOT"/dist/*.rvpkg)
shopt -u nullglob

if [ ${#PKGS[@]} -eq 0 ]; then
    echo "error: no .rvpkg files in $ROOT/dist — run 'make packages' first" >&2
    exit 1
fi

RVPKG="${SEQ_RVPKG:-}"
if [ -z "$RVPKG" ]; then
    RVPKG="$(command -v rvpkg || true)"
fi
if [ -z "$RVPKG" ] && [ -n "${RV_HOME:-}" ] && [ -x "$RV_HOME/bin/rvpkg" ]; then
    RVPKG="$RV_HOME/bin/rvpkg"
fi

if [ -z "$RVPKG" ]; then
    cat >&2 <<'EOF'
error: could not find the 'rvpkg' tool (ships next to rv).
Set SEQ_RVPKG=/path/to/rvpkg or add it to PATH, then re-run.

Manual alternative: in RV, use RV > Preferences > Packages > Add Package...
and pick the files in dist/.
EOF
    exit 1
fi

mkdir -p "$SUPPORT"
echo "Installing ${#PKGS[@]} package(s) into $SUPPORT using $RVPKG"
"$RVPKG" -force -install -add "$SUPPORT" "${PKGS[@]}"
echo "Done. Ensure RV picks up this area (it does by default for ~/.rv,"
echo "otherwise add it to RV_SUPPORT_PATH)."
