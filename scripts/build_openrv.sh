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
#
# Codec opt-ins and other studio build knobs live in configs/build.env
# (sourced below; pre-set environment variables win). On Windows, run this
# from an MSYS2 bash shell per upstream's build instructions.
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

# Studio build configuration of record (codec opt-ins, branding, platform).
if [ -f "$ROOT/configs/build.env" ]; then
    # shellcheck disable=SC1091
    . "$ROOT/configs/build.env"
fi

if [ "${SEQ_APPLY_BRANDING:-1}" = "1" ]; then
    python3 "$ROOT/scripts/apply_branding.py" --openrv "$SRC" --yes
fi

# Legacy single knob: applies to both directions when the split vars are unset.
if [ -n "${SEQ_FFMPEG_NON_FREE:-}" ]; then
    SEQ_FFMPEG_NON_FREE_DECODERS="${SEQ_FFMPEG_NON_FREE_DECODERS:-$SEQ_FFMPEG_NON_FREE}"
    SEQ_FFMPEG_NON_FREE_ENCODERS="${SEQ_FFMPEG_NON_FREE_ENCODERS:-$SEQ_FFMPEG_NON_FREE}"
fi

# Upstream's ffmpeg build reads these to re-enable non-free codecs.
if [ -n "${SEQ_FFMPEG_NON_FREE_DECODERS:-}" ]; then
    export RV_FFMPEG_NON_FREE_DECODERS_TO_ENABLE="$SEQ_FFMPEG_NON_FREE_DECODERS"
    echo "Enabling non-free ffmpeg decoders: $SEQ_FFMPEG_NON_FREE_DECODERS"
fi
if [ -n "${SEQ_FFMPEG_NON_FREE_ENCODERS:-}" ]; then
    export RV_FFMPEG_NON_FREE_ENCODERS_TO_ENABLE="$SEQ_FFMPEG_NON_FREE_ENCODERS"
    echo "Enabling non-free ffmpeg encoders: $SEQ_FFMPEG_NON_FREE_ENCODERS"
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
