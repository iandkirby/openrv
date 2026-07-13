# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Sequence Annotation Export — annotated frames + review report.

Workflow: the session (including RVPaint annotation strokes) is saved to a
temp .rv file, rvio renders just the annotated frames to PNGs, and a
standalone HTML report + JSON payload pairs each frame with its shot and any
notes from the Sequence Notes package.

rvio is located via $SEQ_RVIO_BIN, then PATH, then $RV_HOME/bin — so exports
work from the bundled distribution without configuration.
"""

import os
import shutil
import subprocess
import tempfile

from rv import commands, extra_commands, rvtypes

import sequence_export_core as core

LOG = "[sequence_annotation_export]"
NOTES_PROP = "sequence_notes.data"
SHOT_PROP = "sequence_review.shot"


def _log(msg):
    print("%s %s" % (LOG, msg))


def _qt():
    try:
        from PySide6 import QtWidgets
    except ImportError:
        from PySide2 import QtWidgets
    return QtWidgets


def _get_string_prop(prop, default=""):
    try:
        if commands.propertyExists(prop):
            values = commands.getStringProperty(prop)
            if values:
                return values[0]
    except Exception:
        pass
    return default


def find_rvio():
    path = os.environ.get("SEQ_RVIO_BIN")
    if path and os.path.isfile(path):
        return path
    path = shutil.which("rvio")
    if path:
        return path
    rv_home = os.environ.get("RV_HOME")
    if rv_home:
        for name in ("rvio", "rvio.exe"):
            candidate = os.path.join(rv_home, "bin", name)
            if os.path.isfile(candidate):
                return candidate
    return None


def annotated_frames():
    """Frames carrying paint annotations, falling back to marked frames."""
    try:
        frames = commands.findAnnotatedFrames()
        if frames:
            return sorted(set(int(f) for f in frames))
    except Exception as exc:
        _log("findAnnotatedFrames unavailable (%s); using marked frames" % exc)
    try:
        return sorted(set(int(f) for f in commands.markedFrames()))
    except Exception:
        return []


def _shot_at_frame(frame):
    try:
        srcs = commands.sourcesAtFrame(frame)
        if not srcs:
            return "", None
        group = commands.nodeGroup(srcs[0])
        shot = _get_string_prop("%s.%s" % (group, SHOT_PROP))
        if not shot:
            try:
                shot = extra_commands.uiName(group)
            except Exception:
                shot = group
        return shot, group
    except Exception:
        return "", None


def _notes_for_group(group):
    if group is None:
        return []
    text = _get_string_prop("%s.%s" % (group, NOTES_PROP))
    try:
        import sequence_notes_core

        return sequence_notes_core.loads_notes(text)
    except ImportError:
        import json

        try:
            data = json.loads(text) if text else []
            return data if isinstance(data, list) else []
        except ValueError:
            return []


class SequenceAnnotationExportMode(rvtypes.MinorMode):
    def __init__(self):
        rvtypes.MinorMode.__init__(self)
        self.init(
            "sequence_annotation_export",
            None,
            None,
            [
                ("Sequence", [
                    ("_", None),
                    ("Export Annotated Frames + Report...", self.exportReport, None, None),
                ]),
            ],
        )

    def exportReport(self, event):
        QtWidgets = _qt()
        from rv import qtutils

        out_dir = QtWidgets.QFileDialog.getExistingDirectory(
            qtutils.sessionWindow(), "Choose export directory"
        )
        if not out_dir:
            return
        try:
            result = self._export(out_dir)
        except Exception as exc:
            _log("export failed: %s" % exc)
            self._feedback("Export failed: %s" % exc)
            return
        self._feedback("Report written: %s" % result)

    def _export(self, out_dir):
        frames = annotated_frames()

        # Persist the session (with paint strokes) for rvio.
        tmp_session = os.path.join(
            tempfile.mkdtemp(prefix="sequence_export_"), "session.rv"
        )
        self._save_session(tmp_session)

        rendered = {}
        if frames:
            rvio = find_rvio()
            if rvio:
                cmd = core.rvio_command(rvio, tmp_session, out_dir, frames)
                _log("running: %s" % " ".join(cmd))
                proc = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                )
                if proc.returncode != 0:
                    tail = (proc.stdout or b"").decode("utf-8", "replace")[-2000:]
                    _log("rvio failed (%d):\n%s" % (proc.returncode, tail))
                else:
                    pad = core.pad_for(frames)
                    for f in frames:
                        name = core.image_name(f, pad)
                        if os.path.isfile(os.path.join(out_dir, name)):
                            rendered[f] = name
            else:
                _log("rvio not found — report will reference notes only")
        else:
            _log("no annotated or marked frames — exporting notes-only report")

        meta = {
            "show": os.environ.get("SEQ_SHOW", ""),
            "date": os.environ.get("SEQ_DAILIES_DATE", ""),
            "generated": core.utc_now_iso(),
        }

        entries = []
        for f in frames:
            shot, group = _shot_at_frame(f)
            entries.append(
                {
                    "frame": f,
                    "shot": shot,
                    "image": rendered.get(f),
                    "notes": _notes_for_group(group),
                }
            )

        report_path = os.path.join(out_dir, "report.html")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write(core.report_html(meta, entries))
        with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as fh:
            fh.write(core.report_json(meta, entries))

        _log("wrote %s (%d frame(s), %d rendered)" % (report_path, len(frames), len(rendered)))
        return report_path

    def _save_session(self, path):
        try:
            commands.saveSession(path)
            return
        except Exception as exc:
            _log("commands.saveSession failed (%s); trying Mu fallback" % exc)
        from rv import runtime

        runtime.eval('saveSession("%s");' % path.replace("\\", "/"), ["commands"])

    def _feedback(self, msg):
        try:
            extra_commands.displayFeedback(msg, 4.0)
        except Exception:
            _log(msg)


def createMode():
    return SequenceAnnotationExportMode()
