#!/usr/bin/env python3
# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Build (and validate) the studio .rvpkg files.

An .rvpkg is a zip archive with a PACKAGE manifest at its root plus the mode
files (.py / .mu) and any support files. This script keeps zero third-party
dependencies (no PyYAML) by parsing only the small manifest subset rvpkg uses.

Usage:
    make_packages.py --check              validate manifests only
    make_packages.py --dist dist          validate + build dist/*.rvpkg
"""

import argparse
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGES_DIR = os.path.join(ROOT, "packages")

REQUIRED_KEYS = ("package", "version", "author", "organization", "rv")
MODE_EXTENSIONS = (".py", ".mu")
EXCLUDE_NAMES = {"__pycache__"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".swp")

_TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$")
_MODE_FILE_RE = re.compile(r"^\s*-?\s*file:\s*(\S+)\s*$")


class ManifestError(Exception):
    pass


def parse_manifest(text):
    """Parse the flat subset of YAML used by PACKAGE manifests.

    Returns {"keys": {key: value}, "modes": [file, ...]}.
    """
    keys = {}
    modes = []
    in_modes = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if not in_modes:
            m = _TOP_KEY_RE.match(line)
            if m:
                key, value = m.group(1), m.group(2)
                if key == "modes":
                    in_modes = True
                else:
                    keys[key] = value.strip("'\"")
                continue
        else:
            m = _MODE_FILE_RE.match(line)
            if m:
                modes.append(m.group(1))
                continue
            # A new top-level key ends the modes block.
            if _TOP_KEY_RE.match(line) and not line.startswith((" ", "\t", "-")):
                key, value = _TOP_KEY_RE.match(line).groups()
                keys[key] = value.strip("'\"")
                in_modes = False
    return {"keys": keys, "modes": modes}


def validate_package(pkg_dir):
    """Validate one package directory; returns its parsed manifest."""
    name = os.path.basename(pkg_dir)
    manifest_path = os.path.join(pkg_dir, "PACKAGE")
    if not os.path.isfile(manifest_path):
        raise ManifestError("%s: missing PACKAGE manifest" % name)

    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = parse_manifest(fh.read())

    for key in REQUIRED_KEYS:
        if not manifest["keys"].get(key):
            raise ManifestError("%s: PACKAGE is missing required key '%s'" % (name, key))

    if not manifest["modes"]:
        raise ManifestError("%s: PACKAGE declares no modes" % name)

    for mode in manifest["modes"]:
        candidates = [os.path.join(pkg_dir, mode + ext) for ext in MODE_EXTENSIONS]
        if not any(os.path.isfile(c) for c in candidates):
            raise ManifestError(
                "%s: mode '%s' has no matching %s file"
                % (name, mode, "/".join(MODE_EXTENSIONS))
            )
    return manifest


def package_files(pkg_dir):
    for entry in sorted(os.listdir(pkg_dir)):
        if entry in EXCLUDE_NAMES or entry.startswith("."):
            continue
        if entry.endswith(EXCLUDE_SUFFIXES):
            continue
        path = os.path.join(pkg_dir, entry)
        if os.path.isfile(path):
            yield path


def build_package(pkg_dir, dist_dir):
    manifest = validate_package(pkg_dir)
    name = os.path.basename(pkg_dir)
    version = manifest["keys"]["version"]
    os.makedirs(dist_dir, exist_ok=True)
    out_path = os.path.join(dist_dir, "%s-%s.rvpkg" % (name, version))
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in package_files(pkg_dir):
            zf.write(path, arcname=os.path.basename(path))
    return out_path


def discover_packages(packages_dir=PACKAGES_DIR):
    if not os.path.isdir(packages_dir):
        return []
    return sorted(
        os.path.join(packages_dir, d)
        for d in os.listdir(packages_dir)
        if os.path.isdir(os.path.join(packages_dir, d)) and not d.startswith((".", "_"))
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate only")
    parser.add_argument("--dist", default=os.path.join(ROOT, "dist"), help="output directory")
    parser.add_argument("--packages", default=PACKAGES_DIR, help="packages source directory")
    args = parser.parse_args(argv)

    pkg_dirs = discover_packages(args.packages)
    if not pkg_dirs:
        print("error: no package directories found under %s" % args.packages, file=sys.stderr)
        return 2

    failures = 0
    for pkg_dir in pkg_dirs:
        name = os.path.basename(pkg_dir)
        try:
            if args.check:
                validate_package(pkg_dir)
                print("ok       %s" % name)
            else:
                out = build_package(pkg_dir, args.dist)
                print("built    %s" % os.path.relpath(out, ROOT))
        except ManifestError as exc:
            failures += 1
            print("error    %s" % exc, file=sys.stderr)

    if failures:
        print("%d package(s) failed" % failures, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
