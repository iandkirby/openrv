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

PYBIN="$(command -v python3 || command -v python || true)"
if [ "${SEQ_APPLY_BRANDING:-1}" = "1" ] && [ -n "$PYBIN" ]; then
    "$PYBIN" "$ROOT/scripts/apply_branding.py" --openrv "$SRC" --yes
fi

# Studio source patches (anchored, fail-loud on upstream drift): currently
# extends VideoToolbox hardware decode to HEVC/H.264 on macOS.
if [ "${SEQ_APPLY_SOURCE_PATCHES:-1}" = "1" ] && [ -n "$PYBIN" ]; then
    "$PYBIN" "$ROOT/scripts/patch_openrv.py" --openrv "$SRC"
fi

# Legacy single knob: applies to both directions when the split vars are unset.
if [ -n "${SEQ_FFMPEG_NON_FREE:-}" ]; then
    SEQ_FFMPEG_NON_FREE_DECODERS="${SEQ_FFMPEG_NON_FREE_DECODERS:-$SEQ_FFMPEG_NON_FREE}"
    SEQ_FFMPEG_NON_FREE_ENCODERS="${SEQ_FFMPEG_NON_FREE_ENCODERS:-$SEQ_FFMPEG_NON_FREE}"
fi

# Codec opt-ins are CMAKE LIST VARIABLES in upstream (verified against
# v3.2.0: cmake/dependencies/ffmpeg.cmake re-enables ffmpeg-level decoders,
# and src/lib/image/mio_ffmpeg/CMakeLists.txt turns each list entry into a
# -D__FFMPEG_ENABLE_NON_FREE_DECODER_<name> compile definition that removes
# the codec from RV's runtime disallow list — hevc lives behind that gate).
# They are NOT environment variables; they must be passed as -D cache args,
# semicolon-separated. Comma lists from build.env are converted here.
export SEQ_CODEC_DECODERS_CMAKE="${SEQ_FFMPEG_NON_FREE_DECODERS//,/;}"
export SEQ_CODEC_ENCODERS_CMAKE="${SEQ_FFMPEG_NON_FREE_ENCODERS//,/;}"
# Keep MSYS2 from mangling the semicolon lists on Windows.
export MSYS2_ARG_CONV_EXCL="${MSYS2_ARG_CONV_EXCL:--DRV_FFMPEG_NON_FREE}"
if [ -n "$SEQ_CODEC_DECODERS_CMAKE" ]; then
    echo "Non-free ffmpeg decoders to enable: $SEQ_CODEC_DECODERS_CMAKE"
fi
if [ -n "$SEQ_CODEC_ENCODERS_CMAKE" ]; then
    echo "Non-free ffmpeg encoders to enable: $SEQ_CODEC_ENCODERS_CMAKE"
fi

cd "$SRC"

export RV_VFX_PLATFORM="${RV_VFX_PLATFORM:-CY2024}"
# CMake 4 refuses projects declaring cmake_minimum_required < 3.5, which some
# of OpenRV's vendored dependencies still do; this is CMake's escape hatch.
export CMAKE_POLICY_VERSION_MINIMUM="${CMAKE_POLICY_VERSION_MINIMUM:-3.5}"

if [ -f "rvcmds.sh" ]; then
    echo "Building OpenRV via upstream rvcmds.sh (this takes a while)…"
    echo "  RV_VFX_PLATFORM=$RV_VFX_PLATFORM  QT_HOME=${QT_HOME:-<unset, rvcmds will search>}"
    # rvcmds.sh defines its build commands as aliases, which non-interactive
    # bash ignores unless expand_aliases is on; each command must also sit on
    # its own line so aliases resolve at parse time.
    # Equivalent to upstream's rvbootstrap (rvsetup && rvcfg && rvbuild),
    # with the studio codec cache variables appended between configure and
    # build. Re-running cmake on the build dir with extra -D flags updates
    # the cache and reconfigures.
    bash <<'RVEOF'
shopt -s expand_aliases
source ./rvcmds.sh
rvsetup
rvcfg
if [ -n "${SEQ_CODEC_DECODERS_CMAKE}${SEQ_CODEC_ENCODERS_CMAKE}" ]; then
    cmake -B "${RV_BUILD_DIR}" \
        -DRV_FFMPEG_NON_FREE_DECODERS_TO_ENABLE="${SEQ_CODEC_DECODERS_CMAKE}" \
        -DRV_FFMPEG_NON_FREE_ENCODERS_TO_ENABLE="${SEQ_CODEC_ENCODERS_CMAKE}"
fi
rvbuild
RVEOF
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
