# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
import json
import unittest

import context  # noqa: F401

import sequence_ocio_core as core


RULES_TEXT = json.dumps(
    {
        "config_by_show": {
            "default": "${SEQ_KIT_ROOT}/ocio/config.ocio",
            "SHOWA": "/shows/SHOWA/ocio/config.ocio",
        },
        "working_colorspace": "ACEScg",
        "file_rules": [
            {"pattern": "\\.exr$", "colorspace": "ACEScg"},
            {"pattern": "\\.(mov|mp4)$", "colorspace": "sRGB - Texture"},
        ],
        "display": "sRGB - Display",
        "view": "ACES 1.0 - SDR Video",
    }
)


class LoadRulesTests(unittest.TestCase):
    def test_empty_gives_defaults(self):
        rules = core.load_rules("")
        self.assertEqual(rules["working_colorspace"], "scene_linear")
        self.assertEqual(rules["file_rules"], [])

    def test_merges_over_defaults(self):
        rules = core.load_rules(json.dumps({"display": "P3"}))
        self.assertEqual(rules["display"], "P3")
        self.assertEqual(rules["working_colorspace"], "scene_linear")

    def test_bad_json_raises(self):
        with self.assertRaises(core.RulesError):
            core.load_rules("{nope")
        with self.assertRaises(core.RulesError):
            core.load_rules(json.dumps([1, 2]))


class ShowDetectionTests(unittest.TestCase):
    def test_env_wins(self):
        self.assertEqual(core.detect_show("/shows/SHOWB/x.exr", {"SEQ_SHOW": "SHOWA"}), "SHOWA")

    def test_path_segment(self):
        self.assertEqual(core.detect_show("/shows/SHOWB/sq/sh/x.exr", {}), "SHOWB")
        self.assertEqual(core.detect_show("/projects/apollo/x.exr", {}), "apollo")
        self.assertEqual(core.detect_show("/jobs/j123/x.exr", {}), "j123")

    def test_no_show(self):
        self.assertIsNone(core.detect_show("/tmp/x.exr", {}))


class ConfigResolutionTests(unittest.TestCase):
    def setUp(self):
        self.rules = core.load_rules(RULES_TEXT)

    def test_show_specific_config(self):
        path = core.config_for_show(self.rules, "SHOWA", {})
        self.assertEqual(path, "/shows/SHOWA/ocio/config.ocio")

    def test_default_with_env_expansion(self):
        path = core.config_for_show(self.rules, "UNKNOWN", {"SEQ_KIT_ROOT": "/opt/kit"})
        self.assertEqual(path, "/opt/kit/ocio/config.ocio")

    def test_no_config_returns_none(self):
        self.assertIsNone(core.config_for_show(core.load_rules(""), "SHOWA", {}))

    def test_unset_var_expands_to_empty(self):
        self.assertEqual(core.expand("${MISSING}/x", {}), "/x")


class ColorspaceRuleTests(unittest.TestCase):
    def setUp(self):
        self.rules = core.load_rules(RULES_TEXT)

    def test_first_match_wins(self):
        self.assertEqual(
            core.colorspace_for_media(self.rules, "/x/shot.1001.EXR"), "ACEScg"
        )
        self.assertEqual(
            core.colorspace_for_media(self.rules, "/x/edit.MOV"), "sRGB - Texture"
        )

    def test_no_match_returns_none(self):
        self.assertIsNone(core.colorspace_for_media(self.rules, "/x/notes.txt"))

    def test_invalid_regex_is_skipped(self):
        rules = core.load_rules(
            json.dumps({"file_rules": [
                {"pattern": "([", "colorspace": "broken"},
                {"pattern": "\\.exr$", "colorspace": "good"},
            ]})
        )
        self.assertEqual(core.colorspace_for_media(rules, "a.exr"), "good")

    def test_display_view(self):
        self.assertEqual(
            core.display_view(self.rules), ("sRGB - Display", "ACES 1.0 - SDR Video")
        )
        self.assertEqual(core.display_view(core.load_rules("")), ("", ""))


class RulesPathTests(unittest.TestCase):
    def test_explicit_env_wins(self):
        env = {"SEQ_OCIO_RULES": "/etc/seq/rules.json", "SEQ_KIT_ROOT": "/opt/kit"}
        self.assertEqual(core.resolve_rules_path(env), "/etc/seq/rules.json")

    def test_kit_root_default(self):
        path = core.resolve_rules_path({"SEQ_KIT_ROOT": "/opt/kit"})
        self.assertEqual(path.replace("\\", "/"), "/opt/kit/configs/ocio_rules.json")

    def test_nothing_resolves_to_none(self):
        self.assertIsNone(core.resolve_rules_path({}))


if __name__ == "__main__":
    unittest.main()
