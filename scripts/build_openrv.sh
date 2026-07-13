#!/usr/bin/env bash
# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
#
# Build upstream OpenRV (rv + rvio) from _external/OpenRV, with optional
# studio branding applied first.
#
#   scripts/build_openrv.sh
#
# Environment:
#   SEQ_OPENRV_DIR         source checkout (default _external/OpenRV)
#   SEQ_APPLY_BRANDING=1   swap splash/branding assets before building
#   SEQ_FFMPEG_NON_FREE    optional, e.g. "aac" — passed through to the
#                          upstream build as non-free ffmpeg codecs to enable.
#                          Enabling non-free codecs is a studio licensing
#                          decision; see docs/building-openrv.md.
#
# This is a thin wrapper: the authoritative build steps (system packages,
# Qt, Python version) live in upstream's README and docs/building-openrv.md.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${SEQ_OPENRV_DIR:-$ROOT/_external/OpenRV}"

if [ ! -d "$SRC" ]; then
    echo "error: no OpenRV checkout at $SRC — run scripts/get_openrv.sh first" >&2
    exit 1
fi

if [ "${SEQ_APPLY_BRANDING:-0}" = "1" ]; then
    python3 "$ROOT/scripts/apply_branding.py" --openrv "$SRC" --yes
fi

if [ -n "${SEQ_FFMPEG_NON_FREE:-}" ]; then
    # Upstream reads these to widen the ffmpeg build. Keep decoders/encoders
    # symmetrical unless you know you only need one direction.
    export RV_FFMPEG_NON_FREE_DECODERS_TO_ENABLE="$SEQ_FFMPEG_NON_FREE"
    export RV_FFMPEG_NON_FREE_ENCODERS_TO_ENABLE="$SEQ_FFMPEG_NON_FREE"
    echo "Enabling non-free ffmpeg codecs: $SEQ_FFMPEG_NON_FREE"
fi

cd "$SRC"

if [ -f "rvcmds.sh" ]; then
    echo "Building OpenRV via upstream rvcmds.sh (this takes a while)…"
    # shellcheck disable=SC1091
    bash -c 'source ./rvcmds.sh && rvbootstrap'
else
    cat >&2 <<EOF
error: $SRC/rvcmds.sh not found — the upstream build entrypoint moved.
Follow the build instructions in the upstream README for this version, then
run scripts/bundle_release.sh against the resulting stage directory.
EOF
    exit 1
fi

echo
echo "Build finished. Stage output is under $SRC/_build (look for stage/app)."
echo "Next: make packages && scripts/bundle_release.sh"
