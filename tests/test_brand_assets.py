# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
import base64
import struct
import unittest

import context  # noqa: F401

import make_brand_assets as brand

# A valid 1x1 transparent PNG — the writers only care about PNG blobs, so the
# tests need no Pillow.
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
PNG_SIG = b"\x89PNG\r\n\x1a\n"


class IcoWriterTests(unittest.TestCase):
    def test_header_and_entries(self):
        data = brand.build_ico([(16, TINY_PNG), (256, TINY_PNG)])
        reserved, res_type, count = struct.unpack("<HHH", data[:6])
        self.assertEqual((reserved, res_type, count), (0, 1, 2))

        # First entry: 16px encodes literally; second: 256 encodes as 0.
        self.assertEqual(data[6], 16)
        self.assertEqual(data[6 + 16], 0)

        for i in range(count):
            entry = data[6 + 16 * i : 6 + 16 * (i + 1)]
            size, offset = struct.unpack("<II", entry[8:16])
            self.assertEqual(size, len(TINY_PNG))
            self.assertEqual(data[offset : offset + 8], PNG_SIG)

    def test_total_length(self):
        data = brand.build_ico([(s, TINY_PNG) for s in brand.ICO_SIZES])
        expected = 6 + 16 * len(brand.ICO_SIZES) + len(TINY_PNG) * len(brand.ICO_SIZES)
        self.assertEqual(len(data), expected)


class IcnsWriterTests(unittest.TestCase):
    def test_magic_and_length(self):
        data = brand.build_icns([(b"ic07", TINY_PNG), (b"ic08", TINY_PNG)])
        self.assertEqual(data[:4], b"icns")
        self.assertEqual(struct.unpack(">I", data[4:8])[0], len(data))

    def test_chunk_walk(self):
        entries = [(t, TINY_PNG) for t, _ in brand.ICNS_TYPES]
        data = brand.build_icns(entries)
        pos, found = 8, []
        while pos < len(data):
            ctype = data[pos : pos + 4]
            clen = struct.unpack(">I", data[pos + 4 : pos + 8])[0]
            self.assertEqual(data[pos + 8 : pos + 16], PNG_SIG[:8])
            found.append(ctype)
            pos += clen
        self.assertEqual(pos, len(data))
        self.assertEqual(found, [t for t, _ in brand.ICNS_TYPES])


class RepoAssetTests(unittest.TestCase):
    def test_committed_assets_are_valid(self):
        branding = context.ROOT / "branding"
        ico = (branding / "icon.ico").read_bytes()
        self.assertEqual(struct.unpack("<HH", ico[:4]), (0, 1))
        icns = (branding / "icon.icns").read_bytes()
        self.assertEqual(icns[:4], b"icns")
        self.assertEqual(struct.unpack(">I", icns[4:8])[0], len(icns))
        splash = (branding / "splash.png").read_bytes()
        self.assertEqual(splash[:8], PNG_SIG)
        master = (branding / "logo_master.png").read_bytes()
        self.assertEqual(master[:8], PNG_SIG)


if __name__ == "__main__":
    unittest.main()
