#!/usr/bin/env bash
# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
#
# Fetch upstream OpenRV into _external/OpenRV.
#
#   SEQ_OPENRV_TAG=v3.0.0 scripts/get_openrv.sh
#
# SEQ_OPENRV_TAG defaults to 'main'. For reproducible studio builds, ALWAYS
# pin a release tag from https://github.com/AcademySoftwareFoundation/OpenRV/releases
# and record it alongside the build.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="${SEQ_OPENRV_UPSTREAM:-https://github.com/AcademySoftwareFoundation/OpenRV.git}"
TAG="${SEQ_OPENRV_TAG:-main}"
DEST="${SEQ_OPENRV_DIR:-$ROOT/_external/OpenRV}"

if [ "$TAG" = "main" ]; then
    echo "warning: SEQ_OPENRV_TAG not set — tracking 'main'. Pin a release tag" >&2
    echo "         for anything you intend to deploy to artists." >&2
fi

if [ -d "$DEST/.git" ]; then
    echo "Updating existing checkout at $DEST (-> $TAG)"
    git -C "$DEST" fetch --tags origin
    git -C "$DEST" checkout "$TAG"
    if git -C "$DEST" symbolic-ref -q HEAD >/dev/null; then
        git -C "$DEST" pull --ff-only origin "$TAG"
    fi
    git -C "$DEST" submodule update --init --recursive
else
    mkdir -p "$(dirname "$DEST")"
    echo "Cloning $UPSTREAM ($TAG) into $DEST"
    git clone --recursive --branch "$TAG" "$UPSTREAM" "$DEST"
fi

echo
echo "OpenRV source ready at: $DEST"
echo "Pinned ref: $(git -C "$DEST" describe --tags --always)"
echo "Next: scripts/build_openrv.sh   (prereqs: docs/building-openrv.md)"
