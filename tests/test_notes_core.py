# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
import unittest

import context  # noqa: F401

import sequence_notes_core as core


class NoteTests(unittest.TestCase):
    def test_new_note_fields(self):
        note = core.new_note("  check the roto edge  ", author="rk", status="fix")
        self.assertEqual(note["text"], "check the roto edge")
        self.assertEqual(note["author"], "rk")
        self.assertEqual(note["status"], "fix")
        self.assertRegex(note["created"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_empty_text_raises(self):
        with self.assertRaises(ValueError):
            core.new_note("   ")

    def test_unknown_status_falls_back(self):
        note = core.new_note("x", author="a", status="bogus")
        self.assertEqual(note["status"], core.DEFAULT_STATUS)

    def test_add_and_load_round_trip(self):
        text = ""
        for i in range(3):
            text = core.add_note(text, core.new_note("note %d" % i, author="a"))
        notes = core.loads_notes(text)
        self.assertEqual([n["text"] for n in notes], ["note 0", "note 1", "note 2"])

    def test_loads_notes_tolerates_garbage(self):
        for bad in ("", None, "not json", '{"a": 1}', '["str", 2]'):
            self.assertEqual(core.loads_notes(bad), [])

    def test_format_note_line(self):
        note = core.new_note("fix it", author="rk", status="fix",
                             created="2026-07-13T10:00:00Z")
        line = core.format_note_line(note)
        self.assertIn("[FIX]", line)
        self.assertIn("fix it", line)
        self.assertIn("rk", line)
        self.assertIn("2026-07-13 10:00", line)

    def test_plain_note_has_no_badge(self):
        note = core.new_note("hello", author="a", status="note")
        self.assertFalse(core.format_note_line(note).startswith("["))


class ExportShapeTests(unittest.TestCase):
    def setUp(self):
        self.by_shot = {
            "sh0020": [core.new_note("b", author="x")],
            "sh0010": [core.new_note("a", author="y", status="approved")],
        }

    def test_csv_rows_sorted_with_header(self):
        rows = core.notes_to_csv_rows(self.by_shot)
        self.assertEqual(rows[0], ("shot", "status", "author", "created", "text"))
        self.assertEqual([r[0] for r in rows[1:]], ["sh0010", "sh0020"])

    def test_json_payload_shape(self):
        payload = core.notes_export_payload("SHOWA", self.by_shot)
        self.assertEqual(payload["show"], "SHOWA")
        self.assertIn("generated", payload)
        self.assertEqual(sorted(payload["shots"]), ["sh0010", "sh0020"])

    def test_json_payload_drops_empty_shots(self):
        payload = core.notes_export_payload("S", {"sh0010": [], "sh0020": self.by_shot["sh0020"]})
        self.assertEqual(list(payload["shots"]), ["sh0020"])


if __name__ == "__main__":
    unittest.main()
