# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Pure-Python core for the Sequence Dailies package.

No ``rv`` imports here: everything in this module is unit-testable outside a
running RV. The RV-facing glue lives in sequence_dailies.py.
"""

import bisect
import json
import os


class ManifestError(ValueError):
    """Raised when a dailies manifest is malformed."""


def _default_shot_name(media, index):
    base = os.path.basename(str(media))
    stem = base.split(".", 1)[0]
    return stem or "item%03d" % (index + 1)


def parse_manifest(source):
    """Parse a dailies manifest (dict or JSON text) into a normalized dict.

    Returns::

        {"show": str, "date": str,
         "items": [{"shot", "media", "range", "artist", "status", "note"}]}

    ``range`` is ``[in, out]`` (ints, in <= out) or ``None`` when the item
    should play its full media length.
    """
    if isinstance(source, (str, bytes)):
        try:
            data = json.loads(source)
        except ValueError as exc:
            raise ManifestError("manifest is not valid JSON: %s" % exc)
    else:
        data = source

    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a JSON object")

    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ManifestError("manifest needs a non-empty 'items' list")

    items = []
    for i, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise ManifestError("items[%d] must be an object" % i)
        media = raw.get("media")
        if not media or not isinstance(media, str):
            raise ManifestError("items[%d] is missing 'media'" % i)

        rng = raw.get("range")
        if rng is not None:
            try:
                rng = [int(rng[0]), int(rng[1])]
            except (TypeError, ValueError, IndexError):
                raise ManifestError("items[%d] 'range' must be [in, out]" % i)
            if rng[0] > rng[1]:
                raise ManifestError("items[%d] 'range' is inverted" % i)

        items.append(
            {
                "shot": str(raw.get("shot") or _default_shot_name(media, i)),
                "media": media,
                "range": rng,
                "artist": str(raw.get("artist") or ""),
                "status": str(raw.get("status") or ""),
                "note": str(raw.get("note") or ""),
            }
        )

    return {
        "show": str(data.get("show") or ""),
        "date": str(data.get("date") or ""),
        "items": items,
    }


def durations(items, fallback=1):
    """Frame duration per item; ``fallback`` when an item has no range."""
    out = []
    for item in items:
        rng = item.get("range")
        out.append(rng[1] - rng[0] + 1 if rng else fallback)
    return out


def starts_from_durations(durs, first_frame=1):
    """Global start frame of each item laid end-to-end from ``first_frame``."""
    starts = []
    frame = first_frame
    for d in durs:
        starts.append(frame)
        frame += max(1, int(d))
    return starts


def item_index_for_frame(starts, frame):
    """Index of the item playing at ``frame`` (clamped to valid range)."""
    if not starts:
        raise ValueError("empty starts list")
    idx = bisect.bisect_right(starts, frame) - 1
    return min(max(idx, 0), len(starts) - 1)


def next_start(starts, frame):
    """Start frame of the next item after ``frame`` (wraps to the first)."""
    if not starts:
        raise ValueError("empty starts list")
    for s in starts:
        if s > frame:
            return s
    return starts[0]


def prev_start(starts, frame):
    """Start frame of the previous item before ``frame`` (wraps to the last).

    Sitting exactly on an item's start jumps to the previous item, matching
    how prev-chapter behaves in every player.
    """
    if not starts:
        raise ValueError("empty starts list")
    prior = [s for s in starts if s < frame]
    return prior[-1] if prior else starts[-1]


def dumps_state(manifest, starts):
    """Serialize manifest + computed starts for storage on the RV node."""
    return json.dumps({"manifest": manifest, "starts": list(starts)})


def loads_state(text):
    """Inverse of dumps_state; returns (manifest, starts) or (None, [])."""
    try:
        data = json.loads(text)
        return data["manifest"], [int(s) for s in data["starts"]]
    except (ValueError, KeyError, TypeError):
        return None, []
