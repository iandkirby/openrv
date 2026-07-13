#!/usr/bin/env python3
# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Generate all branding assets from the studio logo master.

Reads branding/logo_master.png (the Sequence circle wordmark, RGBA) and
writes everything the builds and installers consume:

    branding/icon.png    square app icon source (replaces upstream PNG icons)
    branding/splash.png  launch splash (replaces upstream splash at build time)
    branding/icon.ico    Windows icon (exe/installer/shortcuts)
    branding/icon.icns   macOS app bundle icon

The .ico/.icns writers are pure-stdlib (PNG-based entries, supported since
Vista / OS X 10.7); Pillow is only needed for resizing, i.e. only when
running this script — not at test or RV runtime.

Re-run after replacing the master:
    python3 scripts/make_brand_assets.py [--source path/to/logo.png]

A higher-resolution master (>=1024px) improves the large icon sizes; with a
smaller master the large sizes are upscaled, which is acceptable for this
flat two-tone logo.
"""

import argparse
import io
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANDING = os.path.join(ROOT, "branding")
MASTER = os.path.join(BRANDING, "logo_master.png")

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

# PNG-based icns entry types by pixel size (icon + retina variants).
ICNS_TYPES = (
    (b"ic11", 32),   # 16x16@2x
    (b"ic12", 64),   # 32x32@2x
    (b"ic07", 128),
    (b"ic08", 256),
    (b"ic09", 512),
    (b"ic10", 1024), # 512x512@2x
)

SPLASH_SIZE = (800, 450)
SPLASH_BG = (12, 12, 14, 255)
SPLASH_LOGO_HEIGHT = 280


def build_ico(entries):
    """Build a .ico from [(size, png_bytes)] (PNG-compressed entries)."""
    header = struct.pack("<HHH", 0, 1, len(entries))
    directory = b""
    blobs = b""
    offset = len(header) + 16 * len(entries)
    for size, png in entries:
        directory += struct.pack(
            "<BBBBHHII",
            size if size < 256 else 0,   # width; 0 encodes 256
            size if size < 256 else 0,   # height
            0, 0, 1, 32, len(png), offset,
        )
        blobs += png
        offset += len(png)
    return header + directory + blobs


def build_icns(entries):
    """Build a .icns from [(4-byte type, png_bytes)]."""
    body = b""
    for icns_type, png in entries:
        body += icns_type + struct.pack(">I", 8 + len(png)) + png
    return b"icns" + struct.pack(">I", 8 + len(body)) + body


def _png_bytes(image):
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _resized(master, size):
    from PIL import Image

    return master.resize((size, size), Image.LANCZOS)


def generate(source, out_dir=BRANDING):
    from PIL import Image

    master = Image.open(source).convert("RGBA")
    if master.size[0] != master.size[1]:
        side = min(master.size)
        left = (master.size[0] - side) // 2
        top = (master.size[1] - side) // 2
        master = master.crop((left, top, left + side, top + side))

    os.makedirs(out_dir, exist_ok=True)
    written = []

    def emit(name, data):
        path = os.path.join(out_dir, name)
        with open(path, "wb") as fh:
            fh.write(data)
        written.append((name, len(data)))

    if os.path.abspath(source) != os.path.abspath(os.path.join(out_dir, "logo_master.png")):
        emit("logo_master.png", _png_bytes(master))

    emit("icon.png", _png_bytes(_resized(master, 512)))

    splash = Image.new("RGBA", SPLASH_SIZE, SPLASH_BG)
    logo = _resized(master, SPLASH_LOGO_HEIGHT)
    splash.alpha_composite(
        logo,
        (
            (SPLASH_SIZE[0] - SPLASH_LOGO_HEIGHT) // 2,
            (SPLASH_SIZE[1] - SPLASH_LOGO_HEIGHT) // 2,
        ),
    )
    emit("splash.png", _png_bytes(splash.convert("RGB")))

    emit(
        "icon.ico",
        build_ico([(s, _png_bytes(_resized(master, s))) for s in ICO_SIZES]),
    )
    emit(
        "icon.icns",
        build_icns([(t, _png_bytes(_resized(master, s))) for t, s in ICNS_TYPES]),
    )
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=MASTER, help="logo master image")
    parser.add_argument("--out", default=BRANDING, help="output directory")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.source):
        print("error: source image not found: %s" % args.source, file=sys.stderr)
        return 2
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("error: Pillow is required to (re)generate assets: pip install pillow",
              file=sys.stderr)
        return 2

    for name, size in generate(args.source, args.out):
        print("wrote %-16s %6d bytes" % (name, size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
