# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Pure-Python core for the Sequence Notes package (no ``rv`` imports).

Notes are stored per source as a JSON array in a string property on the
source group node, so they persist inside .rv session files and travel with
the session. Each note::

    {"text": str, "author": str, "status": str, "created": iso8601-utc}
"""

import getpass
import json
from datetime import datetime, timezone

STATUSES = ("note", "approved", "cbb", "fix")
DEFAULT_STATUS = "note"


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_author():
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def new_note(text, author=None, status=DEFAULT_STATUS, created=None):
    text = (text or "").strip()
    if not text:
        raise ValueError("note text is empty")
    if status not in STATUSES:
        status = DEFAULT_STATUS
    return {
        "text": text,
        "author": author or default_author(),
        "status": status,
        "created": created or utc_now_iso(),
    }


def loads_notes(text):
    """Tolerant parse: anything malformed yields an empty list."""
    if not text:
        return []
    try:
        data = json.loads(text)
    except ValueError:
        return []
    if not isinstance(data, list):
        return []
    return [n for n in data if isinstance(n, dict) and n.get("text")]


def dumps_notes(notes):
    return json.dumps(list(notes))


def add_note(existing_text, note):
    """Append ``note`` to a serialized note list; returns new serialized text."""
    notes = loads_notes(existing_text)
    notes.append(note)
    return dumps_notes(notes)


def format_note_line(note):
    status = note.get("status", DEFAULT_STATUS)
    prefix = "" if status == DEFAULT_STATUS else "[%s] " % status.upper()
    when = note.get("created", "")[:16].replace("T", " ")
    return "%s%s — %s %s" % (prefix, note.get("text", ""), note.get("author", "?"), when)


def notes_to_csv_rows(notes_by_shot):
    """Flatten {shot: [notes]} into CSV rows with a header row first."""
    rows = [("shot", "status", "author", "created", "text")]
    for shot in sorted(notes_by_shot):
        for note in notes_by_shot[shot]:
            rows.append(
                (
                    shot,
                    note.get("status", ""),
                    note.get("author", ""),
                    note.get("created", ""),
                    note.get("text", ""),
                )
            )
    return rows


def notes_export_payload(show, notes_by_shot, generated=None):
    """Stable JSON structure for handing notes to other tools."""
    return {
        "show": show,
        "generated": generated or utc_now_iso(),
        "shots": {
            shot: list(notes) for shot, notes in sorted(notes_by_shot.items()) if notes
        },
    }
