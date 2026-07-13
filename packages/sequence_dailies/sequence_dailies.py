# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Sequence Dailies — build a review session from a JSON manifest.

Creates one source per manifest item, tags it with shot metadata (consumed by
the sequence_hud and sequence_notes packages), assembles everything into a
sequence node, marks shot boundaries, and binds next/prev-shot hotkeys.

Entry points:
  * Sequence menu -> Load Dailies Manifest…
  * $SEQ_DAILIES_MANIFEST at startup (set by the seqrv launcher)
"""

import os

from rv import commands, extra_commands, rvtypes

import sequence_dailies_core as core

LOG = "[sequence_dailies]"
STATE_PROP = "sequence_dailies.state"
REVIEW_COMP = "sequence_review"


def _log(msg):
    print("%s %s" % (LOG, msg))


def _ensure_string_prop(prop, value):
    try:
        if not commands.propertyExists(prop):
            commands.newProperty(prop, commands.StringType, 1)
        commands.setStringProperty(prop, [str(value)], True)
    except Exception as exc:
        _log("could not set %s: %s" % (prop, exc))


def _get_string_prop(prop, default=""):
    try:
        if commands.propertyExists(prop):
            values = commands.getStringProperty(prop)
            if values:
                return values[0]
    except Exception:
        pass
    return default


def _set_ui_name(node, name):
    try:
        extra_commands.setUIName(node, name)
    except Exception:
        pass


class SequenceDailiesMode(rvtypes.MinorMode):
    def __init__(self):
        rvtypes.MinorMode.__init__(self)
        self._starts = []
        self._seq_node = None
        self._last_path = None

        self.init(
            "sequence_dailies",
            [
                ("session-initialized", self.onSessionInitialized,
                 "Auto-load $SEQ_DAILIES_MANIFEST"),
                ("key-down--alt--right", self.nextShot, "Go to next shot"),
                ("key-down--alt--left", self.prevShot, "Go to previous shot"),
            ],
            None,
            [
                ("Sequence", [
                    ("Load Dailies Manifest...", self.loadManifestDialog, None, None),
                    ("Reload Last Manifest", self.reloadManifest, None, self._reloadState),
                    ("_", None),
                    ("Next Shot", self.nextShot, None, None),
                    ("Previous Shot", self.prevShot, None, None),
                ]),
            ],
        )

    # -- session building ---------------------------------------------------

    def loadManifestPath(self, path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                manifest = core.parse_manifest(fh.read())
        except (OSError, core.ManifestError) as exc:
            _log("failed to load %s: %s" % (path, exc))
            self._feedback("Dailies manifest failed: %s" % exc)
            return

        self._last_path = path
        self._buildSession(manifest)

    def _buildSession(self, manifest):
        items = manifest["items"]
        groups = []
        for item in items:
            group = self._addItem(item)
            if group:
                groups.append((group, item))

        if not groups:
            self._feedback("Dailies: no sources could be loaded")
            return

        seq = commands.newNode("RVSequenceGroup", "dailiesSequence")
        commands.setNodeInputs(seq, [g for g, _ in groups])
        label = "Dailies %s %s" % (manifest.get("show", ""), manifest.get("date", ""))
        _set_ui_name(seq, label.strip() or "Dailies")
        commands.setViewNode(seq)

        starts = self._computeStarts(seq, [item for _, item in groups])
        self._starts = starts
        self._seq_node = seq

        for frame in starts:
            try:
                commands.markFrame(frame, True)
            except Exception:
                pass

        _ensure_string_prop(
            "%s.%s" % (seq, STATE_PROP), core.dumps_state(manifest, starts)
        )

        if starts:
            commands.setFrame(starts[0])
        try:
            commands.redraw()
        except Exception:
            pass
        _log("built dailies session: %d item(s)" % len(groups))
        self._feedback("Dailies loaded: %d shots" % len(groups))

    def _addItem(self, item):
        try:
            src = commands.addSourceVerbose([item["media"]])
        except Exception as exc:
            _log("could not add %s: %s" % (item["media"], exc))
            return None

        group = commands.nodeGroup(src)

        rng = item.get("range")
        if rng:
            for prop, value in (("cut.in", rng[0]), ("cut.out", rng[1])):
                full = "%s.%s" % (src, prop)
                try:
                    commands.setIntProperty(full, [int(value)], True)
                except Exception as exc:
                    _log("could not set %s: %s" % (full, exc))

        for key in ("shot", "artist", "status", "note"):
            if item.get(key):
                _ensure_string_prop("%s.%s.%s" % (group, REVIEW_COMP, key), item[key])

        _set_ui_name(group, item["shot"])
        return group

    def _computeStarts(self, seq_group, items):
        """Prefer the sequence node's own EDL (ground truth for actual media
        lengths); fall back to manifest ranges when it is unavailable."""
        try:
            seq_nodes = [
                n for n in commands.nodesInGroup(seq_group)
                if commands.nodeType(n) == "RVSequence"
            ]
            if seq_nodes:
                edl = commands.getIntProperty("%s.edl.frame" % seq_nodes[0])
                if edl and len(edl) >= len(items):
                    return [int(f) for f in edl[: len(items)]]
        except Exception as exc:
            _log("EDL start-frame query failed (%s); using manifest ranges" % exc)
        return core.starts_from_durations(core.durations(items, fallback=1))

    # -- persistence across session reload ----------------------------------

    def _loadStateFromView(self):
        try:
            view = commands.viewNode()
        except Exception:
            return False
        state = _get_string_prop("%s.%s" % (view, STATE_PROP))
        if not state:
            return False
        manifest, starts = core.loads_state(state)
        if not starts:
            return False
        self._starts = starts
        self._seq_node = view
        return True

    # -- event handlers ------------------------------------------------------

    def onSessionInitialized(self, event):
        event.reject()
        path = os.environ.get("SEQ_DAILIES_MANIFEST")
        if path:
            if os.path.isfile(path):
                _log("auto-loading manifest from SEQ_DAILIES_MANIFEST")
                self.loadManifestPath(path)
            else:
                _log("SEQ_DAILIES_MANIFEST points at a missing file: %s" % path)

    def loadManifestDialog(self, event):
        try:
            from rv import qtutils

            try:
                from PySide6 import QtWidgets
            except ImportError:
                from PySide2 import QtWidgets

            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                qtutils.sessionWindow(),
                "Load Dailies Manifest",
                os.environ.get("SEQ_DAILIES_DIR", ""),
                "Dailies manifests (*.json);;All files (*)",
            )
        except Exception as exc:
            _log("file dialog unavailable: %s" % exc)
            return
        if path:
            self.loadManifestPath(path)

    def reloadManifest(self, event):
        if self._last_path:
            self.loadManifestPath(self._last_path)

    def _reloadState(self):
        if self._last_path:
            return commands.NeutralMenuState
        return commands.DisabledMenuState

    def nextShot(self, event):
        self._jump(core.next_start)

    def prevShot(self, event):
        self._jump(core.prev_start)

    def _jump(self, chooser):
        if not self._starts and not self._loadStateFromView():
            # No dailies session: fall back to marked frames if any.
            try:
                marked = sorted(commands.markedFrames())
            except Exception:
                marked = []
            if not marked:
                self._feedback("No dailies session loaded")
                return
            self._starts = marked
        try:
            frame = commands.frame()
            commands.setFrame(chooser(self._starts, frame))
        except Exception as exc:
            _log("shot navigation failed: %s" % exc)

    def _feedback(self, msg):
        try:
            extra_commands.displayFeedback(msg, 3.0)
        except Exception:
            _log(msg)


def createMode():
    return SequenceDailiesMode()
