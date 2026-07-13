#!/usr/bin/env python3
# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Resolve the OCIO config path for a show from the studio rules file.

Usage: resolve_ocio.py <rules.json> [show]

Prints the config path when it resolves to an existing file; prints nothing
otherwise, and always exits 0 — launchers call it unconditionally. Shared by
bin/seqrv, bin/seqrvio, and their Windows .cmd counterparts.

Works from two layouts: the repo (imports the core module from packages/)
and a bundled distribution (bundle_release.sh drops sequence_ocio_core.py
next to this file).
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _candidate in (
    os.path.join(os.path.dirname(_HERE), "packages", "sequence_ocio"),
    _HERE,
):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

import sequence_ocio_core as core  # noqa: E402


def resolve(rules_path, show, env):
    """Existing OCIO config path for ``show`` per the rules file, or None."""
    try:
        with open(rules_path, "r", encoding="utf-8") as fh:
            rules = core.load_rules(fh.read())
    except (OSError, core.RulesError):
        return None
    config = core.config_for_show(rules, show or None, env)
    if config and os.path.isfile(config):
        return config
    return None


def main(argv):
    if len(argv) < 2:
        return 0
    show = argv[2] if len(argv) > 2 else None
    path = resolve(argv[1], show, dict(os.environ))
    if path:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
