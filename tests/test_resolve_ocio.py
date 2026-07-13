# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
import json
import tempfile
import unittest
from pathlib import Path

import context  # noqa: F401

import resolve_ocio


class ResolveOcioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)

        self.config = root / "config.ocio"
        self.config.write_text("ocio_profile_version: 2\n")

        self.rules = root / "rules.json"
        self.rules.write_text(json.dumps({
            "config_by_show": {
                "default": "${ROOTVAR}/config.ocio",
                "SHOWA": str(self.config),
                "GHOST": str(root / "missing" / "config.ocio"),
            }
        }))
        self.env = {"ROOTVAR": str(root)}

    def test_show_specific_config(self):
        self.assertEqual(
            resolve_ocio.resolve(str(self.rules), "SHOWA", self.env), str(self.config)
        )

    def test_default_via_env_expansion(self):
        self.assertEqual(
            resolve_ocio.resolve(str(self.rules), "UNKNOWN", self.env), str(self.config)
        )
        self.assertEqual(
            resolve_ocio.resolve(str(self.rules), None, self.env), str(self.config)
        )

    def test_missing_config_file_returns_none(self):
        self.assertIsNone(resolve_ocio.resolve(str(self.rules), "GHOST", {}))

    def test_unreadable_or_bad_rules_return_none(self):
        self.assertIsNone(resolve_ocio.resolve(str(self.rules) + ".nope", "SHOWA", {}))
        bad = Path(self.tmp.name) / "bad.json"
        bad.write_text("{nope")
        self.assertIsNone(resolve_ocio.resolve(str(bad), "SHOWA", {}))


if __name__ == "__main__":
    unittest.main()
