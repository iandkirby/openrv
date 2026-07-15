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

  nv12-semiplanar-hwdecode:
      Companion to hw-decode-hevc-h264. VideoToolbox 8-bit HEVC/H.264 decode
      returns a SEMI-planar NV12 source frame, but decodeImageAtFrame builds a
      FULLY-planar Y/U/V destination and (source being 8-bit) skips conversion,
      so av_image_copy aborts (imgutils.c:351). Detect an 8-bit semi-planar
      source frame, remap to the matching fully-planar YUV, re-stride, and force
      an sws_scale conversion. Applied AFTER hw-decode-hevc-h264.
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


# ---------------------------------------------------------------------------
# nv12-semiplanar-hwdecode:
#     VideoToolbox 8-bit HEVC/H.264 hardware decode hands back a SEMI-planar
#     source frame (NV12: Y + one interleaved CbCr plane), but
#     decodeImageAtFrame builds a FULLY-planar Y/U/V destination and (because
#     the source is 8-bit) leaves convertFormat=false, so copyFrame's
#     av_image_copy tries to copy the interleaved-chroma NV12 source into a
#     planar U/V layout and libavutil aborts (dst_linesize >= bytewidth,
#     imgutils.c:351 -> SIGABRT). Detect an 8-bit semi-planar SOURCE frame in
#     the default/planar branch, remap nativeFormat to the matching
#     fully-planar YUV, re-fill outFrame->linesize (so all three planes are
#     strided correctly even if sw_pix_fmt were itself semi-planar), and force
#     a real sws_scale conversion -- the same path HW 10-bit/ProRes already
#     use. Keying on the decoded SOURCE frame (not sw_pix_fmt) leaves
#     fully-planar software decode and the >8-bit P010/ProRes paths untouched.
#     Only reachable once hw-decode-hevc-h264 has widened the VideoToolbox
#     trigger to HEVC/H.264, so it is applied AFTER patch_hw_decode.
# ---------------------------------------------------------------------------

NV12_ANCHOR = re.compile(
    r"(                convertFormat = \(bitSize != 8\);\n)"
    r"(                numPlanes = av_pix_fmt_count_planes\(nativeFormat\);)"
)

NV12_INSERT = (
    "                //\n"
    "                // Sequence Group: semi-planar (NV12) hardware-decode fix.\n"
    "                // VideoToolbox 8-bit HEVC/H.264 hardware decode yields a\n"
    "                // SEMI-planar SOURCE frame (NV12: Y plane + one interleaved\n"
    "                // CbCr plane) while the destination built below is FULLY\n"
    "                // planar (separate U and V). A non-converting av_image_copy\n"
    "                // of that source asserts in libavutil (chroma bytewidth\n"
    "                // ~width > destination U-plane stride ~width/2 -> SIGABRT at\n"
    "                // imgutils.c:351). Detect an 8-bit semi-planar SOURCE frame,\n"
    "                // remap nativeFormat to the matching fully-planar YUV, re-fill\n"
    "                // outFrame->linesize so all three planes are strided\n"
    "                // correctly, and force a real sws_scale conversion. Keying on\n"
    "                // the decoded source frame (not sw_pix_fmt) leaves fully-planar\n"
    "                // software decode and the >8-bit P010/ProRes paths untouched.\n"
    "                {\n"
    "                    const AVPixelFormat srcFormat = static_cast<AVPixelFormat>(videoFrame->format);\n"
    "                    const AVPixFmtDescriptor* srcDesc = av_pix_fmt_desc_get(srcFormat);\n"
    "                    if (srcDesc != nullptr && (srcDesc->comp[0].depth - srcDesc->comp[0].shift) == 8\n"
    "                        && (srcDesc->flags & AV_PIX_FMT_FLAG_PLANAR) && !(srcDesc->flags & AV_PIX_FMT_FLAG_RGB)\n"
    "                        && av_pix_fmt_count_planes(srcFormat) < srcDesc->nb_components)\n"
    "                    {\n"
    "                        int slog2w, slog2h;\n"
    "                        av_pix_fmt_get_chroma_sub_sample(srcFormat, &slog2w, &slog2h);\n"
    "                        nativeFormat = (slog2w == 1 && slog2h == 1)   ? AV_PIX_FMT_YUV420P\n"
    "                                       : (slog2w == 1 && slog2h == 0) ? AV_PIX_FMT_YUV422P\n"
    "                                                                      : AV_PIX_FMT_YUV444P;\n"
    "                        outFrame->format = nativeFormat;\n"
    "                        av_image_fill_arrays(outFrame->data, outFrame->linesize, nullptr, nativeFormat, width, height, 1 /*align*/);\n"
    "                        convertFormat = true;\n"
    "                    }\n"
    "                }\n"
)

NV12_ALREADY = "Sequence Group: semi-planar (NV12) hardware-decode fix"


def patch_nv12_semiplanar(openrv_dir):
    """Returns 'patched', 'already', or raises RuntimeError."""
    path = os.path.join(openrv_dir, MFF)
    if not os.path.isfile(path):
        raise RuntimeError("%s not found -- upstream layout changed?" % path)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()

    if NV12_ANCHOR.search(text) is None:
        # Anchor stops matching once patched (the two anchored lines are then
        # separated by the inserted block); the marker is the idempotency guard.
        if NV12_ALREADY in text:
            return "already"
        raise RuntimeError(
            "nv12-semiplanar anchor not found in %s -- upstream code moved; "
            "update scripts/patch_openrv.py before building" % MFF
        )

    # Replacement FUNCTION (not a template string) so nothing in NV12_INSERT is
    # interpreted as a backreference/escape.
    new_text, count = NV12_ANCHOR.subn(
        lambda m: m.group(1) + NV12_INSERT + m.group(2), text, count=1
    )
    if count != 1:
        raise RuntimeError(
            "expected exactly one nv12-semiplanar anchor, replaced %d" % count
        )
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

    try:
        nv12_result = patch_nv12_semiplanar(args.openrv)
    except RuntimeError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("nv12-semiplanar-hwdecode: %s" % nv12_result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
