# Copyright (c) 2026 The Sequence Group.
# SPDX-License-Identifier: Apache-2.0
"""Pure-Python core for the Sequence OCIO package (no ``rv`` imports).

Studio color rules live in a JSON file (default: configs/ocio_rules.json in
the kit root, overridable via $SEQ_OCIO_RULES)::

    {
      "config_by_show": {"default": "${SEQ_CONFIG_ROOT}/ocio/config.ocio",
                          "SHOWA": "/shows/SHOWA/ocio/config.ocio"},
      "working_colorspace": "scene_linear",
      "file_rules": [{"pattern": "\\.exr$", "colorspace": "ACEScg"}, ...],
      "display": "sRGB - Display",
      "view": "ACES 1.0 - SDR Video"
    }

``file_rules`` are evaluated top-down with ``re.search`` (case-insensitive);
the first match wins.
"""

import json
import os
import re

DEFAULT_RULES = {
    "config_by_show": {},
    "working_colorspace": "scene_linear",
    "file_rules": [],
    "display": "",
    "view": "",
}

_SHOW_PATH_RE = re.compile(r"/(?:shows?|projects?|jobs?)/([^/]+)/", re.IGNORECASE)


class RulesError(ValueError):
    """Raised when the rules file is malformed."""


def load_rules(text):
    """Parse rules JSON text merged over DEFAULT_RULES ('' / None -> defaults)."""
    if not text:
        return dict(DEFAULT_RULES)
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise RulesError("OCIO rules file is not valid JSON: %s" % exc)
    if not isinstance(data, dict):
        raise RulesError("OCIO rules root must be a JSON object")
    rules = dict(DEFAULT_RULES)
    rules.update(data)
    return rules


def expand(path, env):
    """Expand ${VAR} references from ``env`` (unset vars become '')."""
    return re.sub(r"\$\{(\w+)\}", lambda m: env.get(m.group(1), ""), path or "")


def detect_show(media_path, env):
    """Show name from $SEQ_SHOW, else from a /shows/<name>/ path segment."""
    show = env.get("SEQ_SHOW")
    if show:
        return show
    m = _SHOW_PATH_RE.search(media_path or "")
    return m.group(1) if m else None


def config_for_show(rules, show, env):
    """Absolute OCIO config path for ``show`` (or the default), or None."""
    configs = rules.get("config_by_show") or {}
    raw = configs.get(show) if show else None
    if not raw:
        raw = configs.get("default")
    if not raw:
        return None
    path = expand(raw, env)
    return path or None


def colorspace_for_media(rules, media_path):
    """First matching file_rules colorspace for ``media_path``, or None."""
    for rule in rules.get("file_rules") or []:
        pattern = rule.get("pattern")
        colorspace = rule.get("colorspace")
        if not pattern or not colorspace:
            continue
        try:
            if re.search(pattern, media_path or "", re.IGNORECASE):
                return colorspace
        except re.error:
            continue
    return None


def display_view(rules):
    """(display, view) tuple; empty strings mean 'leave RV's default alone'."""
    return rules.get("display") or "", rules.get("view") or ""


def resolve_rules_path(env):
    """Where the rules file lives: $SEQ_OCIO_RULES, else kit default."""
    explicit = env.get("SEQ_OCIO_RULES")
    if explicit:
        return explicit
    kit_root = env.get("SEQ_KIT_ROOT")
    if kit_root:
        return os.path.join(kit_root, "configs", "ocio_rules.json")
    return None
