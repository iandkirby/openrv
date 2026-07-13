# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
import json
import unittest

import context  # noqa: F401

import sequence_export_core as core


class FrameRangeTests(unittest.TestCase):
    def test_collapses_consecutive_runs(self):
        self.assertEqual(core.frames_to_ranges([1, 2, 3, 10, 12, 13]), "1-3,10,12-13")

    def test_dedupes_and_sorts(self):
        self.assertEqual(core.frames_to_ranges([5, 1, 5, 2]), "1-2,5")

    def test_single_and_empty(self):
        self.assertEqual(core.frames_to_ranges([42]), "42")
        self.assertEqual(core.frames_to_ranges([]), "")


class NamingTests(unittest.TestCase):
    def test_pad_minimum_four(self):
        self.assertEqual(core.pad_for([1, 99]), 4)

    def test_pad_grows_with_frame_numbers(self):
        self.assertEqual(core.pad_for([100001]), 6)

    def test_pattern_and_name_agree(self):
        pad = core.pad_for([1001])
        self.assertEqual(core.image_pattern(pad), "annotated.@@@@.png")
        self.assertEqual(core.image_name(1001, pad), "annotated.1001.png")
        self.assertEqual(core.image_name(7, pad), "annotated.0007.png")


class RvioCommandTests(unittest.TestCase):
    def test_command_shape(self):
        cmd = core.rvio_command("/opt/rv/bin/rvio", "/tmp/s.rv", "/tmp/out", [1001, 1002])
        self.assertEqual(cmd[0], "/opt/rv/bin/rvio")
        self.assertEqual(cmd[1], "/tmp/s.rv")
        self.assertEqual(cmd[cmd.index("-t") + 1], "1001-1002")
        self.assertTrue(cmd[cmd.index("-o") + 1].endswith("annotated.@@@@.png"))


class ReportTests(unittest.TestCase):
    META = {"show": "SHOWA", "date": "2026-07-13", "generated": "2026-07-13T10:00:00Z"}
    ENTRIES = [
        {
            "frame": 1001,
            "shot": "sh0010",
            "image": "annotated.1001.png",
            "notes": [{"text": "fix <edge>", "author": "rk", "status": "fix",
                       "created": "2026-07-13T09:00:00Z"}],
        },
        {"frame": 1050, "shot": "sh0020", "image": None, "notes": []},
    ]

    def test_html_contains_frames_and_escapes(self):
        html_text = core.report_html(self.META, self.ENTRIES)
        self.assertIn("annotated.1001.png", html_text)
        self.assertIn("sh0010", html_text)
        self.assertIn("fix &lt;edge&gt;", html_text)
        self.assertNotIn("fix <edge>", html_text)
        self.assertIn("no rendered frame", html_text)
        self.assertIn("SHOWA", html_text)

    def test_json_report_round_trips(self):
        data = json.loads(core.report_json(self.META, self.ENTRIES))
        self.assertEqual(data["show"], "SHOWA")
        self.assertEqual(len(data["frames"]), 2)
        self.assertEqual(data["frames"][0]["frame"], 1001)


if __name__ == "__main__":
    unittest.main()
