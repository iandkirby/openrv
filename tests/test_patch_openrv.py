# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path

import context  # noqa: F401

import patch_openrv

# Mirrors the relevant upstream structure at OpenRV v3.2.0.
UPSTREAM_SNIPPET = """\
        }

#if defined(RV_FFMPEG_USE_VIDEOTOOLBOX)
        if (avStream->codecpar->codec_id == AV_CODEC_ID_PRORES)
        {
            if (!videoToolboxInit(avCodec, avCodecContext, hardwareContext))
            {
                static std::once_flag warnOnce;
            }
        }
#endif

        // Open the codec
        (*avCodecContext)->thread_count = m_io->codecThreads();
"""


class PatchHwDecodeTests(unittest.TestCase):
    def _make_tree(self, content):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        target = Path(tmp.name) / patch_openrv.MFF
        target.parent.mkdir(parents=True)
        target.write_text(content)
        return tmp.name, target

    def test_patches_upstream_snippet(self):
        root, target = self._make_tree(UPSTREAM_SNIPPET)
        self.assertEqual(patch_openrv.patch_hw_decode(root), "patched")
        text = target.read_text()
        self.assertIn("AV_CODEC_ID_HEVC", text)
        self.assertIn("AV_CODEC_ID_H264", text)
        # Structure preserved: condition still flows into videoToolboxInit.
        self.assertRegex(
            text,
            r"AV_CODEC_ID_PRORES\s*\n\s*\|\| avStream->codecpar->codec_id == "
            r"AV_CODEC_ID_HEVC\s*\n\s*\|\| avStream->codecpar->codec_id == "
            r"AV_CODEC_ID_H264\)\s*\n\s*\{\s*\n\s*if \(!videoToolboxInit",
        )

    def test_idempotent(self):
        root, target = self._make_tree(UPSTREAM_SNIPPET)
        patch_openrv.patch_hw_decode(root)
        first = target.read_text()
        self.assertEqual(patch_openrv.patch_hw_decode(root), "already")
        self.assertEqual(target.read_text(), first)

    def test_fails_loudly_when_upstream_moves(self):
        root, _ = self._make_tree("totally different code\n")
        with self.assertRaises(RuntimeError):
            patch_openrv.patch_hw_decode(root)


# Mirrors the relevant upstream structure at OpenRV v3.2.0: the two adjacent
# lines in decodeImageAtFrame's planar branch that the NV12 fix wedges between.
NV12_SNIPPET = """\
            if (isPlanar && !isRGB)
            {
                convertFormat = (bitSize != 8);
                numPlanes = av_pix_fmt_count_planes(nativeFormat);
                int log2w, log2h;
            }
"""


class PatchNv12SemiplanarTests(unittest.TestCase):
    def _make_tree(self, content):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        target = Path(tmp.name) / patch_openrv.MFF
        target.parent.mkdir(parents=True)
        target.write_text(content)
        return tmp.name, target

    def test_patches_nv12_snippet(self):
        root, target = self._make_tree(NV12_SNIPPET)
        self.assertEqual(patch_openrv.patch_nv12_semiplanar(root), "patched")
        text = target.read_text()
        # Marker inserted exactly once; conversion forced exactly once.
        self.assertEqual(text.count(patch_openrv.NV12_ALREADY), 1)
        self.assertEqual(text.count("                        convertFormat = true;"), 1)
        # numPlanes line survives and now trails the inserted block.
        self.assertIn(
            "                numPlanes = av_pix_fmt_count_planes(nativeFormat);", text
        )
        # Self-contained insert keeps braces balanced.
        self.assertEqual(text.count("{"), text.count("}"))
        # Anchor no longer matches (the two lines are now separated).
        self.assertIsNone(patch_openrv.NV12_ANCHOR.search(text))

    def test_idempotent(self):
        root, target = self._make_tree(NV12_SNIPPET)
        patch_openrv.patch_nv12_semiplanar(root)
        first = target.read_text()
        self.assertEqual(patch_openrv.patch_nv12_semiplanar(root), "already")
        self.assertEqual(target.read_text(), first)

    def test_fails_loudly_when_upstream_moves(self):
        root, _ = self._make_tree("totally different code\n")
        with self.assertRaises(RuntimeError):
            patch_openrv.patch_nv12_semiplanar(root)


if __name__ == "__main__":
    unittest.main()
