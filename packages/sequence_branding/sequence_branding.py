# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Sequence Branding — runtime identity for the studio build.

Window title, About box, and a startup hello. Compile-time assets (splash,
icons) are handled at build time by scripts/apply_branding.py; this package
covers everything that can be done live so it also works on a stock OpenRV.
"""

import os

from rv import commands, extra_commands, rvtypes

KIT_NAME = "Sequence RV"
STUDIO = "The Sequence Group"
KIT_VERSION = "0.1.0"
CONTACT = "software@thesequencegroup.com"

LOG = "[sequence_branding]"


def _log(msg):
    print("%s %s" % (LOG, msg))


class SequenceBrandingMode(rvtypes.MinorMode):
    def __init__(self):
        rvtypes.MinorMode.__init__(self)
        self._greeted = False

        self.init(
            "sequence_branding",
            [
                ("session-initialized", self.onSessionEvent, "Apply studio window title"),
                ("after-session-read", self.onSessionEvent, "Apply studio window title"),
                ("source-group-complete", self.onSessionEvent, "Apply studio window title"),
            ],
            None,
            [
                ("Sequence", [
                    ("_", None),
                    ("About %s..." % KIT_NAME, self.about, None, None),
                ]),
            ],
        )

    def _title(self):
        session = ""
        try:
            session = os.path.basename(commands.sessionFileName() or "")
        except Exception:
            pass
        show = os.environ.get("SEQ_SHOW", "")
        parts = [KIT_NAME]
        if show:
            parts.append(show)
        if session and session != "Untitled":
            parts.append(session)
        return " — ".join(parts)

    def onSessionEvent(self, event):
        event.reject()
        try:
            from rv import qtutils

            window = qtutils.sessionWindow()
            if window is not None:
                window.setWindowTitle(self._title())
        except Exception as exc:
            _log("could not set window title: %s" % exc)

        if not self._greeted:
            self._greeted = True
            try:
                extra_commands.displayFeedback(
                    "%s kit %s — %s" % (KIT_NAME, KIT_VERSION, STUDIO), 3.0
                )
            except Exception:
                pass

    def about(self, event):
        text = (
            "<h3>%s</h3>"
            "<p>%s studio build of OpenRV.</p>"
            "<p>Kit version %s<br>Contact: %s</p>"
            "<p>Built on Academy Software Foundation OpenRV.</p>"
            % (KIT_NAME, STUDIO, KIT_VERSION, CONTACT)
        )
        try:
            from rv import qtutils

            try:
                from PySide6 import QtWidgets
            except ImportError:
                from PySide2 import QtWidgets

            QtWidgets.QMessageBox.about(
                qtutils.sessionWindow(), "About %s" % KIT_NAME, text
            )
        except Exception as exc:
            _log("about dialog unavailable: %s" % exc)
            _log("%s %s (%s) — %s" % (KIT_NAME, KIT_VERSION, STUDIO, CONTACT))


def createMode():
    return SequenceBrandingMode()
