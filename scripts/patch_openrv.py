#!/usr/bin/env python3
# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Apply Sequence Group source patches to an OpenRV checkout.

Unlike blind .patch files, each patch here anchors on exact upstream code and
FAILS LOUDLY when the anchor is missing — so an upstream version bump that
moves the code is caught at build time instead of silently shipping without
the fix. Patches are idempotent (safe to re-run).

Current patches (verified against OpenRV v3.2.0):

  hw-decode-hevc-h264:
      MovieFFMpeg has complete VideoToolbox hardware-decode support but only
      engages it for ProRes (src/lib/image/MovieFFMpeg/MovieFFMpeg.cpp).
      Extend the trigger to HEVC and H.264 so 4K/6K h.265 review material
      uses the Mac's hardware decoder. videoToolboxInit() falls back to
      software decoding when hardware is unavailable, so this is safe on
      all machines. (The whole block is compiled only when
      RV_FFMPEG_USE_VIDEOTOOLBOX is on — macOS arm64 default — so Windows
      and Linux builds are untouched.)
"""

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MFF = os.path.join("src", "lib", "image", "MovieFFMpeg", "MovieFFMpeg.cpp")

HW_ANCHOR = re.compile(
    r"(#if defined\(RV_FFMPEG_USE_VIDEOTOOLBOX\)\s*\n"
    r"\s*if \(avStream->codecpar->codec_id == AV_CODEC_ID_PRORES)(\))"
    r"(\s*\n\s*\{\s*\n\s*if \(!videoToolboxInit)"
)

HW_REPLACEMENT = (
    r"\1"
    r"\n                || avStream->codecpar->codec_id == AV_CODEC_ID_HEVC"
    r"\n                || avStream->codecpar->codec_id == AV_CODEC_ID_H264\2\3"
)

HW_ALREADY = "AV_CODEC_ID_HEVC"


def patch_hw_decode(openrv_dir):
    """Returns 'patched', 'already', or raises RuntimeError."""
    path = os.path.join(openrv_dir, MFF)
    if not os.path.isfile(path):
        raise RuntimeError("%s not found — upstream layout changed?" % path)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()

    window = HW_ANCHOR.search(text)
    if window is None:
        if HW_ALREADY in text and "videoToolboxInit" in text:
            return "already"
        raise RuntimeError(
            "hw-decode anchor not found in %s — upstream code moved; "
            "update scripts/patch_openrv.py before building" % MFF
        )

    new_text, count = HW_ANCHOR.subn(HW_REPLACEMENT, text, count=1)
    if count != 1:
        raise RuntimeError("expected exactly one hw-decode anchor, replaced %d" % count)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    return "patched"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openrv", default=os.path.join(ROOT, "_external", "OpenRV"))
    args = parser.parse_args(argv)

    if not os.path.isdir(args.openrv):
        print("error: OpenRV checkout not found at %s" % args.openrv, file=sys.stderr)
        return 2

    try:
        result = patch_hw_decode(args.openrv)
    except RuntimeError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("hw-decode-hevc-h264: %s" % result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
