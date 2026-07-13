# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import context

import make_packages


class ManifestValidationTests(unittest.TestCase):
    def test_all_repo_packages_validate(self):
        pkg_dirs = make_packages.discover_packages()
        self.assertGreaterEqual(len(pkg_dirs), 6)
        for pkg_dir in pkg_dirs:
            manifest = make_packages.validate_package(pkg_dir)
            self.assertTrue(manifest["modes"], pkg_dir)

    def test_parse_manifest_subset(self):
        manifest = make_packages.parse_manifest(
            "package: Thing\n"
            "version: 1.2\n"
            "requires: ''\n"
            "# comment\n"
            "modes:\n"
            "  - file: thing_mode\n"
            "    load: immediate\n"
        )
        self.assertEqual(manifest["keys"]["package"], "Thing")
        self.assertEqual(manifest["keys"]["requires"], "")
        self.assertEqual(manifest["modes"], ["thing_mode"])

    def test_missing_mode_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "broken_pkg"
            pkg.mkdir()
            (pkg / "PACKAGE").write_text(
                "package: Broken\nversion: 1.0\nauthor: a\norganization: o\nrv: 1.0\n"
                "modes:\n  - file: missing_mode\n"
            )
            with self.assertRaises(make_packages.ManifestError):
                make_packages.validate_package(str(pkg))


class BuildTests(unittest.TestCase):
    def test_builds_all_rvpkgs_with_expected_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            for pkg_dir in make_packages.discover_packages():
                out = make_packages.build_package(pkg_dir, tmp)
                self.assertTrue(out.endswith(".rvpkg"))
                with zipfile.ZipFile(out) as zf:
                    names = zf.namelist()
                    self.assertIn("PACKAGE", names)
                    self.assertTrue(
                        any(n.endswith((".py", ".mu")) for n in names),
                        "%s has no mode files" % out,
                    )
                    # rvpkg expects a flat archive.
                    self.assertTrue(all("/" not in n for n in names), names)

    def test_dailies_package_carries_core_module(self):
        pkg_dir = str(context.ROOT / "packages" / "sequence_dailies")
        with tempfile.TemporaryDirectory() as tmp:
            out = make_packages.build_package(pkg_dir, tmp)
            with zipfile.ZipFile(out) as zf:
                self.assertIn("sequence_dailies_core.py", zf.namelist())


class RepoConfigTests(unittest.TestCase):
    def test_example_manifest_parses_with_dailies_core(self):
        import sequence_dailies_core as dailies_core

        text = (context.ROOT / "examples" / "dailies_example.json").read_text()
        manifest = dailies_core.parse_manifest(text)
        self.assertEqual(manifest["show"], "SHOWA")
        self.assertEqual(len(manifest["items"]), 3)

    def test_repo_ocio_rules_load_and_resolve(self):
        import sequence_ocio_core as ocio_core

        text = (context.ROOT / "configs" / "ocio_rules.json").read_text()
        rules = ocio_core.load_rules(text)
        env = {"SEQ_KIT_ROOT": str(context.ROOT)}
        config = ocio_core.config_for_show(rules, None, env)
        self.assertTrue(Path(config).is_file(), config)
        self.assertEqual(ocio_core.colorspace_for_media(rules, "x.exr"), "linear")
        self.assertEqual(ocio_core.colorspace_for_media(rules, "x.mov"), "sRGB")

    def test_example_manifest_is_valid_json(self):
        json.loads((context.ROOT / "examples" / "dailies_example.json").read_text())


if __name__ == "__main__":
    unittest.main()
