# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Pure-Python core for the Sequence Annotation Export package.

Everything here is testable without RV: frame-range math for rvio, output
naming, and the standalone HTML review report.
"""

import html
import json
from datetime import datetime, timezone

IMAGE_BASENAME = "annotated"


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def frames_to_ranges(frames):
    """Collapse frames into rvio's -t range syntax: [1,2,3,10] -> '1-3,10'."""
    frames = sorted(set(int(f) for f in frames))
    if not frames:
        return ""
    spans = []
    start = prev = frames[0]
    for f in frames[1:]:
        if f == prev + 1:
            prev = f
            continue
        spans.append((start, prev))
        start = prev = f
    spans.append((start, prev))
    return ",".join("%d" % a if a == b else "%d-%d" % (a, b) for a, b in spans)


def pad_for(frames):
    """Frame-number padding wide enough for every frame (minimum 4)."""
    widest = max((len(str(int(f))) for f in frames), default=4)
    return max(4, widest)


def image_pattern(pad):
    """rvio output pattern, e.g. 'annotated.@@@@.png' for pad 4."""
    return "%s.%s.png" % (IMAGE_BASENAME, "@" * pad)


def image_name(frame, pad):
    """Concrete file name rvio writes for ``frame`` under ``pad``."""
    return "%s.%0*d.png" % (IMAGE_BASENAME, pad, int(frame))


def report_json(meta, entries):
    """Machine-readable companion to the HTML report."""
    return json.dumps(
        {
            "show": meta.get("show", ""),
            "date": meta.get("date", ""),
            "generated": meta.get("generated") or utc_now_iso(),
            "frames": entries,
        },
        indent=2,
    )


def _note_html(note):
    status = note.get("status", "note")
    badge = (
        '<span class="badge badge-%s">%s</span> ' % (html.escape(status), html.escape(status))
        if status != "note"
        else ""
    )
    return '<li>%s%s <span class="meta">— %s %s</span></li>' % (
        badge,
        html.escape(note.get("text", "")),
        html.escape(note.get("author", "?")),
        html.escape(note.get("created", "")[:16].replace("T", " ")),
    )


def report_html(meta, entries):
    """Standalone HTML review report.

    ``entries`` is a list of dicts: {"frame": int, "shot": str,
    "image": relative path or None, "notes": [note, ...]}.
    """
    title = "Review report — %s %s" % (meta.get("show", ""), meta.get("date", ""))
    title = title.strip().rstrip("—").strip() or "Review report"

    blocks = []
    for entry in entries:
        img = (
            '<img src="%s" alt="frame %d">' % (html.escape(entry["image"]), entry["frame"])
            if entry.get("image")
            else '<div class="noimg">no rendered frame</div>'
        )
        notes = "".join(_note_html(n) for n in entry.get("notes", []))
        notes_html = "<ul>%s</ul>" % notes if notes else '<p class="meta">no notes</p>'
        blocks.append(
            '<section class="frame">'
            "<h2>%s <span class=\"meta\">frame %d</span></h2>%s%s</section>"
            % (html.escape(entry.get("shot", "")), entry["frame"], img, notes_html)
        )

    return """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 15px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 60rem; padding: 0 1rem; }
  h1 { font-size: 1.4rem; }
  h2 { font-size: 1.05rem; margin: 0 0 .5rem; }
  .meta { color: #888; font-weight: normal; font-size: .85em; }
  .frame { border-top: 1px solid #8884; padding: 1.25rem 0; }
  .frame img { max-width: 100%%; height: auto; border-radius: 4px; }
  .noimg { padding: 2rem; text-align: center; color: #888; border: 1px dashed #8886; border-radius: 4px; }
  .badge { padding: 0 .4em; border-radius: 3px; font-size: .8em; text-transform: uppercase; background: #8883; }
  .badge-approved { background: #2e7d3244; }
  .badge-fix { background: #c6282844; }
  .badge-cbb { background: #f9a82544; }
  ul { padding-left: 1.2rem; }
</style>
<h1>%(title)s</h1>
<p class="meta">generated %(generated)s — The Sequence Group</p>
%(blocks)s
</html>
""" % {
        "title": html.escape(title),
        "generated": html.escape(meta.get("generated") or utc_now_iso()),
        "blocks": "\n".join(blocks),
    }


def rvio_command(rvio_bin, session_path, out_dir, frames, extra_args=()):
    """Assemble the rvio argv that renders the annotated frames."""
    import os

    pad = pad_for(frames)
    return [
        rvio_bin,
        session_path,
        "-t",
        frames_to_ranges(frames),
        "-o",
        os.path.join(out_dir, image_pattern(pad)),
    ] + list(extra_args)
