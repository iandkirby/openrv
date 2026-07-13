# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Test path setup: makes package core modules and scripts importable."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_PATHS = [
    ROOT / "scripts",
    ROOT / "packages" / "sequence_dailies",
    ROOT / "packages" / "sequence_notes",
    ROOT / "packages" / "sequence_annotation_export",
    ROOT / "packages" / "sequence_ocio",
]

for path in _PATHS:
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)
