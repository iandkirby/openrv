# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Sequence Notes — dockable per-shot notes panel.

Notes are stored on each source group (component ``sequence_notes``) so they
persist in the .rv session file. The panel follows the current shot as the
playhead moves. Notes can be exported to JSON (interchange format shared with
sequence_annotation_export) or CSV.

Toggle with alt+n or Sequence -> Notes Panel.
"""

import csv
import json
import os

from rv import commands, extra_commands, rvtypes

import sequence_notes_core as core

LOG = "[sequence_notes]"
NOTES_PROP = "sequence_notes.data"
SHOT_PROP = "sequence_review.shot"


def _log(msg):
    print("%s %s" % (LOG, msg))


def _qt():
    try:
        from PySide6 import QtCore, QtWidgets
    except ImportError:
        from PySide2 import QtCore, QtWidgets
    return QtCore, QtWidgets


def _get_string_prop(prop, default=""):
    try:
        if commands.propertyExists(prop):
            values = commands.getStringProperty(prop)
            if values:
                return values[0]
    except Exception:
        pass
    return default


def _set_string_prop(prop, value):
    try:
        if not commands.propertyExists(prop):
            commands.newProperty(prop, commands.StringType, 1)
        commands.setStringProperty(prop, [str(value)], True)
        return True
    except Exception as exc:
        _log("could not set %s: %s" % (prop, exc))
        return False


def _shot_name(group):
    name = _get_string_prop("%s.%s" % (group, SHOT_PROP))
    if name:
        return name
    try:
        return extra_commands.uiName(group)
    except Exception:
        return group


def current_source_group():
    try:
        srcs = commands.sourcesAtFrame(commands.frame())
        if srcs:
            return commands.nodeGroup(srcs[0])
    except Exception:
        pass
    return None


def all_notes_by_shot():
    """Collect {shot: [notes]} across every source in the session."""
    result = {}
    try:
        sources = commands.nodesOfType("RVFileSource")
    except Exception:
        sources = []
    for src in sources:
        try:
            group = commands.nodeGroup(src)
        except Exception:
            continue
        notes = core.loads_notes(_get_string_prop("%s.%s" % (group, NOTES_PROP)))
        if notes:
            result.setdefault(_shot_name(group), []).extend(notes)
    return result


class SequenceNotesMode(rvtypes.MinorMode):
    def __init__(self):
        rvtypes.MinorMode.__init__(self)
        self._dock = None
        self._widgets = None
        self._current_group = None

        self.init(
            "sequence_notes",
            [
                ("key-down--alt--n", self.toggleDock, "Toggle notes panel"),
                ("frame-changed", self.onFrameChanged, "Refresh notes panel"),
                ("after-graph-view-change", self.onFrameChanged, "Refresh notes panel"),
            ],
            None,
            [
                ("Sequence", [
                    ("Notes Panel", self.toggleDock, None, self._dockState),
                    ("Export Notes (JSON)...", self.exportJson, None, None),
                    ("Export Notes (CSV)...", self.exportCsv, None, None),
                ]),
            ],
        )

    # -- dock construction ---------------------------------------------------

    def _buildDock(self):
        QtCore, QtWidgets = _qt()
        from rv import qtutils

        main = qtutils.sessionWindow()
        dock = QtWidgets.QDockWidget("Sequence Notes", main)
        dock.setObjectName("sequenceNotesDock")

        body = QtWidgets.QWidget(dock)
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(8, 8, 8, 8)

        shot_label = QtWidgets.QLabel("—")
        shot_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(shot_label)

        note_list = QtWidgets.QListWidget()
        note_list.setWordWrap(True)
        layout.addWidget(note_list, 1)

        editor = QtWidgets.QPlainTextEdit()
        editor.setPlaceholderText("New note for this shot…")
        editor.setFixedHeight(70)
        layout.addWidget(editor)

        row = QtWidgets.QHBoxLayout()
        status_box = QtWidgets.QComboBox()
        status_box.addItems(list(core.STATUSES))
        row.addWidget(status_box)
        add_btn = QtWidgets.QPushButton("Add Note")
        add_btn.clicked.connect(self._addNote)
        row.addWidget(add_btn)
        layout.addLayout(row)

        dock.setWidget(body)
        main.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        self._dock = dock
        self._widgets = {
            "shot": shot_label,
            "list": note_list,
            "editor": editor,
            "status": status_box,
        }

    # -- panel state ----------------------------------------------------------

    def _refresh(self, force=False):
        if not self._dock or not self._dock.isVisible():
            return
        group = current_source_group()
        if group == self._current_group and not force:
            return
        self._current_group = group

        w = self._widgets
        if group is None:
            w["shot"].setText("—")
            w["list"].clear()
            return

        w["shot"].setText(_shot_name(group))
        w["list"].clear()
        for note in core.loads_notes(_get_string_prop("%s.%s" % (group, NOTES_PROP))):
            w["list"].addItem(core.format_note_line(note))

    def _addNote(self):
        group = current_source_group()
        if group is None:
            _log("no current source to attach the note to")
            return
        w = self._widgets
        text = w["editor"].toPlainText()
        try:
            note = core.new_note(text, status=w["status"].currentText())
        except ValueError:
            return
        prop = "%s.%s" % (group, NOTES_PROP)
        if _set_string_prop(prop, core.add_note(_get_string_prop(prop), note)):
            w["editor"].setPlainText("")
            self._refresh(force=True)
            try:
                extra_commands.displayFeedback("Note added to %s" % _shot_name(group), 2.0)
            except Exception:
                pass

    # -- exports ---------------------------------------------------------------

    def _savePath(self, caption, filter_text, default_name):
        QtCore, QtWidgets = _qt()
        from rv import qtutils

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            qtutils.sessionWindow(), caption, default_name, filter_text
        )
        return path

    def exportJson(self, event):
        notes = all_notes_by_shot()
        if not notes:
            _log("no notes to export")
            return
        path = self._savePath("Export Notes (JSON)", "JSON (*.json)", "sequence_notes.json")
        if not path:
            return
        payload = core.notes_export_payload(os.environ.get("SEQ_SHOW", ""), notes)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        _log("wrote %s" % path)

    def exportCsv(self, event):
        notes = all_notes_by_shot()
        if not notes:
            _log("no notes to export")
            return
        path = self._savePath("Export Notes (CSV)", "CSV (*.csv)", "sequence_notes.csv")
        if not path:
            return
        with open(path, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerows(core.notes_to_csv_rows(notes))
        _log("wrote %s" % path)

    # -- events -----------------------------------------------------------------

    def toggleDock(self, event):
        try:
            if self._dock is None:
                self._buildDock()
                self._refresh(force=True)
                return
            visible = self._dock.isVisible()
            self._dock.setVisible(not visible)
            if not visible:
                self._refresh(force=True)
        except Exception as exc:
            _log("notes panel unavailable: %s" % exc)

    def onFrameChanged(self, event):
        event.reject()
        self._refresh()

    def _dockState(self):
        if self._dock is not None and self._dock.isVisible():
            return commands.CheckedMenuState
        return commands.UncheckedMenuState


def createMode():
    return SequenceNotesMode()
