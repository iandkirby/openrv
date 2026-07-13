# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
import json
import unittest

import context  # noqa: F401  (sys.path setup)

import sequence_dailies_core as core


MANIFEST = {
    "show": "SHOWA",
    "date": "2026-07-13",
    "items": [
        {"shot": "sh0010", "media": "/x/sh0010.####.exr", "range": [1001, 1010]},
        {"media": "/x/plate_bg.####.exr", "range": [1001, 1005], "artist": "rk"},
        {"shot": "sh0030", "media": "/x/sh0030.mov"},
    ],
}


class ParseManifestTests(unittest.TestCase):
    def test_parses_dict_and_json_text(self):
        for source in (MANIFEST, json.dumps(MANIFEST)):
            parsed = core.parse_manifest(source)
            self.assertEqual(parsed["show"], "SHOWA")
            self.assertEqual(len(parsed["items"]), 3)

    def test_defaults_shot_name_from_media(self):
        parsed = core.parse_manifest(MANIFEST)
        self.assertEqual(parsed["items"][1]["shot"], "plate_bg")

    def test_missing_range_is_none(self):
        parsed = core.parse_manifest(MANIFEST)
        self.assertIsNone(parsed["items"][2]["range"])

    def test_range_normalized_to_ints(self):
        parsed = core.parse_manifest(
            {"items": [{"media": "x.mov", "range": ["1001", "1002"]}]}
        )
        self.assertEqual(parsed["items"][0]["range"], [1001, 1002])

    def test_rejects_bad_manifests(self):
        bad = [
            "not json {",
            json.dumps([]),
            json.dumps({}),
            json.dumps({"items": []}),
            json.dumps({"items": [{"shot": "no_media"}]}),
            json.dumps({"items": [{"media": "x.mov", "range": [10, 1]}]}),
            json.dumps({"items": [{"media": "x.mov", "range": [10]}]}),
        ]
        for source in bad:
            with self.assertRaises(core.ManifestError, msg=source):
                core.parse_manifest(source)


class FrameMathTests(unittest.TestCase):
    def setUp(self):
        parsed = core.parse_manifest(MANIFEST)
        durs = core.durations(parsed["items"], fallback=25)
        self.assertEqual(durs, [10, 5, 25])
        self.starts = core.starts_from_durations(durs)

    def test_starts(self):
        self.assertEqual(self.starts, [1, 11, 16])

    def test_item_index_for_frame(self):
        self.assertEqual(core.item_index_for_frame(self.starts, 1), 0)
        self.assertEqual(core.item_index_for_frame(self.starts, 10), 0)
        self.assertEqual(core.item_index_for_frame(self.starts, 11), 1)
        self.assertEqual(core.item_index_for_frame(self.starts, 999), 2)
        self.assertEqual(core.item_index_for_frame(self.starts, -5), 0)

    def test_next_start_wraps(self):
        self.assertEqual(core.next_start(self.starts, 1), 11)
        self.assertEqual(core.next_start(self.starts, 11), 16)
        self.assertEqual(core.next_start(self.starts, 40), 1)

    def test_prev_start_wraps_and_steps_off_boundary(self):
        self.assertEqual(core.prev_start(self.starts, 12), 11)
        self.assertEqual(core.prev_start(self.starts, 11), 1)
        self.assertEqual(core.prev_start(self.starts, 1), 16)

    def test_empty_starts_raise(self):
        for fn in (core.item_index_for_frame, core.next_start, core.prev_start):
            with self.assertRaises(ValueError):
                fn([], 1)


class StateRoundTripTests(unittest.TestCase):
    def test_round_trip(self):
        manifest = core.parse_manifest(MANIFEST)
        text = core.dumps_state(manifest, [1, 11, 16])
        loaded_manifest, starts = core.loads_state(text)
        self.assertEqual(loaded_manifest, manifest)
        self.assertEqual(starts, [1, 11, 16])

    def test_bad_state_is_tolerated(self):
        self.assertEqual(core.loads_state("junk"), (None, []))
        self.assertEqual(core.loads_state(""), (None, []))


if __name__ == "__main__":
    unittest.main()
