#!/usr/bin/env python3
# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Apply Sequence Group branding assets to an OpenRV source checkout.

OpenRV's splash screen and window icons are compile-time image assets in the
upstream source tree. Runtime branding (window title, About box) is handled by
the sequence_branding package; this script only handles the baked-in images.

It works by filename pattern rather than hard-coded paths, because the asset
locations move between upstream releases:

  * branding/splash.png   -> replaces images whose name contains 'splash'
  * branding/icon.png     -> replaces images whose name contains 'RV.icon' / 'rv_icon'

Nothing happens for assets you have not provided. Originals are backed up
next to the target with a '.orig' suffix (first run only), so this is
re-runnable and reversible.
"""

import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANDING = os.path.join(ROOT, "branding")

RULES = (
    # (our asset, filename substrings to match, extensions to match)
    ("splash.png", ("splash",), (".png", ".jpg", ".jpeg", ".tif", ".tiff")),
    ("icon.png", ("rv.icon", "rv_icon", "openrv.icon"), (".png",)),
    ("icon.ico", ("rv",), (".ico",)),
    ("icon.icns", ("rv",), (".icns",)),
)


def find_targets(openrv_dir, substrings, extensions):
    for dirpath, dirnames, filenames in os.walk(openrv_dir):
        # Skip build output and VCS noise.
        dirnames[:] = [d for d in dirnames if d not in ("_build", ".git", "_install")]
        for fn in filenames:
            low = fn.lower()
            if low.endswith(extensions) and any(s in low for s in substrings):
                yield os.path.join(dirpath, fn)


def apply(openrv_dir, assume_yes):
    replaced = 0
    for asset, substrings, extensions in RULES:
        src = os.path.join(BRANDING, asset)
        if not os.path.isfile(src):
            print("skip: branding/%s not present" % asset)
            continue
        targets = sorted(find_targets(openrv_dir, substrings, extensions))
        if not targets:
            print("warn: no targets matched for %s (upstream layout changed?)" % asset)
            continue
        print("%s will replace:" % asset)
        for t in targets:
            print("  %s" % os.path.relpath(t, openrv_dir))
        if not assume_yes:
            answer = input("Proceed? [y/N] ").strip().lower()
            if answer not in ("y", "yes"):
                print("skipped %s" % asset)
                continue
        for t in targets:
            backup = t + ".orig"
            if not os.path.exists(backup):
                shutil.copy2(t, backup)
            shutil.copy2(src, t)
            replaced += 1
    return replaced


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openrv", default=os.path.join(ROOT, "_external", "OpenRV"))
    parser.add_argument("--yes", action="store_true", help="do not prompt")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.openrv):
        print("error: OpenRV checkout not found at %s" % args.openrv, file=sys.stderr)
        return 2

    replaced = apply(args.openrv, args.yes)
    print("replaced %d asset file(s)" % replaced)
    return 0


if __name__ == "__main__":
    sys.exit(main())
