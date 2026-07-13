# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Sequence OCIO — per-show color pipeline setup.

On startup: resolves the show's OCIO config from the studio rules file and
exports $OCIO if the environment does not already pin one, then switches the
display pipelines to OCIODisplay with the configured display/view.

Per source: assigns the input colorspace from the rules' file_rules by
swapping the source's linearize pipeline to an OCIOFile node.

This package is a studio-tuned replacement for the approach in OpenRV's
bundled ``ocio_source_setup`` example package. If no OCIO config can be
resolved, it deliberately does nothing and RV's default color management
stays in effect. The OCIO node property names below follow the upstream
package; verify against your built OpenRV version on first smoke-test
(everything logs under [sequence_ocio]).

Disable per-session with SEQ_OCIO_DISABLE=1.
"""

import os

from rv import commands, rvtypes

import sequence_ocio_core as core

LOG = "[sequence_ocio]"


def _log(msg):
    print("%s %s" % (LOG, msg))


def _set_string(prop, value):
    if not commands.propertyExists(prop):
        commands.newProperty(prop, commands.StringType, 1)
    commands.setStringProperty(prop, [str(value)], True)


def _set_int(prop, value):
    if not commands.propertyExists(prop):
        commands.newProperty(prop, commands.IntType, 1)
    commands.setIntProperty(prop, [int(value)], True)


def _nodes_in_group_of_type(group, node_type):
    try:
        return [
            n for n in commands.nodesInGroup(group)
            if commands.nodeType(n) == node_type
        ]
    except Exception:
        return []


def _swap_pipeline(pipeline_group, ocio_node_type):
    """Point a pipeline group at a single OCIO node and return that node."""
    _set_string("%s.pipeline.nodes" % pipeline_group, ocio_node_type)
    nodes = _nodes_in_group_of_type(pipeline_group, ocio_node_type)
    return nodes[0] if nodes else None


class SequenceOCIOMode(rvtypes.MinorMode):
    def __init__(self):
        rvtypes.MinorMode.__init__(self)
        self._rules = None
        self._announced = False

        self._resolveEnvironment()

        self.init(
            "sequence_ocio",
            [
                ("source-group-complete", self.onSourceGroupComplete,
                 "Assign OCIO input colorspace per source"),
                ("session-initialized", self.onSessionInitialized,
                 "Configure OCIO display pipeline"),
            ],
            None,
            [
                ("Sequence", [
                    ("Reload OCIO Rules", self.reloadRules, None, None),
                ]),
            ],
        )

    # -- rules / environment --------------------------------------------------

    def _disabled(self):
        return os.environ.get("SEQ_OCIO_DISABLE") == "1"

    def rules(self):
        if self._rules is None:
            path = core.resolve_rules_path(os.environ)
            text = ""
            if path and os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        text = fh.read()
                    _log("rules loaded from %s" % path)
                except OSError as exc:
                    _log("cannot read rules %s: %s" % (path, exc))
            elif path:
                _log("no rules file at %s — using defaults" % path)
            try:
                self._rules = core.load_rules(text)
            except core.RulesError as exc:
                _log(str(exc))
                self._rules = core.load_rules(None)
        return self._rules

    def _resolveEnvironment(self):
        """Export $OCIO from the studio rules unless already pinned."""
        if self._disabled():
            _log("disabled via SEQ_OCIO_DISABLE")
            return
        if os.environ.get("OCIO"):
            _log("honoring existing OCIO=%s" % os.environ["OCIO"])
            return
        show = os.environ.get("SEQ_SHOW")
        config = core.config_for_show(self.rules(), show, os.environ)
        if config and os.path.isfile(config):
            os.environ["OCIO"] = config
            _log("OCIO=%s (show: %s)" % (config, show or "default"))
        elif config:
            _log("resolved config does not exist: %s" % config)
        else:
            _log("no OCIO config resolved — RV default color management active")

    def reloadRules(self, event):
        self._rules = None
        self.rules()

    # -- event handlers ---------------------------------------------------------

    def onSourceGroupComplete(self, event):
        event.reject()
        if self._disabled() or not os.environ.get("OCIO"):
            return
        try:
            group = event.contents().split(";;")[0]
            self._setupSource(group)
        except Exception as exc:
            _log("source setup failed: %s" % exc)

    def _setupSource(self, group):
        sources = _nodes_in_group_of_type(group, "RVFileSource")
        if not sources:
            return
        try:
            media = commands.sourceMedia(sources[0])[0]
        except Exception:
            return

        rules = self.rules()
        colorspace = core.colorspace_for_media(rules, media)
        if not colorspace:
            return

        pipelines = _nodes_in_group_of_type(group, "RVLinearizePipelineGroup")
        if not pipelines:
            _log("no linearize pipeline in %s" % group)
            return

        node = _swap_pipeline(pipelines[0], "OCIOFile")
        if node is None:
            _log("could not create OCIOFile node in %s" % pipelines[0])
            return

        _set_string("%s.ocio.function" % node, "color")
        _set_string("%s.ocio.inColorSpace" % node, colorspace)
        _set_string(
            "%s.ocio_color.outColorSpace" % node,
            rules.get("working_colorspace", "scene_linear"),
        )
        _set_int("%s.ocio.active" % node, 1)
        _log("%s: %s -> %s" % (os.path.basename(media), colorspace,
                               rules.get("working_colorspace")))

    def onSessionInitialized(self, event):
        event.reject()
        if self._disabled() or not os.environ.get("OCIO"):
            return
        display, view = core.display_view(self.rules())
        if not display:
            return
        try:
            for pipeline in commands.nodesOfType("RVDisplayPipelineGroup"):
                node = _swap_pipeline(pipeline, "OCIODisplay")
                if node is None:
                    continue
                _set_string("%s.ocio.function" % node, "display")
                _set_string("%s.ocio_display.display" % node, display)
                if view:
                    _set_string("%s.ocio_display.view" % node, view)
                _set_int("%s.ocio.active" % node, 1)
                _log("display pipeline %s -> %s / %s" % (pipeline, display, view))
        except Exception as exc:
            _log("display setup failed: %s" % exc)


def createMode():
    return SequenceOCIOMode()
