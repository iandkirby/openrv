//
// Copyright (c) 2026 The Sequence Group.
// SPDX-License-Identifier: Apache-2.0
//
// sequence_hud — shot metadata heads-up display for review sessions.
//
// Draws a small text block in the lower-left corner of the view with the
// current shot name, artist, status, and media file, read from the
// "sequence_review" properties that the sequence_dailies package writes onto
// each source group. Falls back to the source's UI name and media path for
// sessions that were not built from a dailies manifest.
//
// Toggle with alt+h or Sequence -> Shot HUD.
//

module: sequence_hud {

use rvtypes;
use commands;
use extra_commands;
use gl;
use gltext;
use app_utils;

class: SequenceHUDMinorMode : MinorMode
{
    bool _visible;

    method: propOr (string; string name, string dflt)
    {
        try
        {
            if (propertyExists(name))
            {
                let v = getStringProperty(name);
                if (v.size() > 0 && v[0] != "") return v[0];
            }
        }
        catch (...)
        {
            ;
        }
        return dflt;
    }

    // named toggleHUD, NOT toggle: rvtypes.Mode.toggle(void;) is RV's own
    // activate/deactivate hook — shadowing it crashes RV's mode teardown on quit
    method: toggleHUD (void; Event event)
    {
        _visible = !_visible;
        redraw();
    }

    method: hudState (int;)
    {
        if (_visible) return CheckedMenuState;
        return UncheckedMenuState;
    }

    method: render (void; Event event)
    {
        if (!_visible) return;

        let d = event.domain(),
            w = d.x,
            h = d.y;

        let f = frame(),
            srcs = sourcesAtFrame(f);

        if (srcs.size() == 0) return;

        let src = srcs[0],
            group = nodeGroup(src);

        string media = "";
        try
        {
            let mlist = getStringProperty(src + ".media.movie");
            if (mlist.size() > 0) media = mlist[0];
        }
        catch (...)
        {
            ;
        }

        if (media != "")
        {
            let parts = media.split("/");
            if (parts.size() > 0) media = parts[parts.size() - 1];
        }

        string fallbackName = group;
        try
        {
            fallbackName = uiName(group);
        }
        catch (...)
        {
            ;
        }

        let shot   = propOr("%s.sequence_review.shot" % group, fallbackName),
            artist = propOr("%s.sequence_review.artist" % group, ""),
            status = propOr("%s.sequence_review.status" % group, "");

        string[] lines;
        lines.push_back("%s   frame %d" % (shot, f));
        if (artist != "") lines.push_back("artist  %s" % artist);
        if (status != "") lines.push_back("status  %s" % status);
        if (media != "")  lines.push_back(media);

        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(0.0, w, 0.0, h, -1.0, 1.0);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();

        gltext.size(14);

        float x = 24.0;
        float y = 24.0;

        for (int i = lines.size() - 1; i >= 0; i--)
        {
            let t = lines[i];
            gltext.color(Color(0.0, 0.0, 0.0, 0.85));
            gltext.writeAt(x + 1.0, y - 1.0, t);
            gltext.color(Color(0.95, 0.95, 0.95, 1.0));
            gltext.writeAt(x, y, t);
            y += 20.0;
        }
    }

    method: SequenceHUDMinorMode (SequenceHUDMinorMode;)
    {
        _visible = true;

        init("sequence-hud",
             [ ("key-down--alt--h", toggleHUD, "Toggle Sequence shot HUD") ],
             nil,
             Menu {
                 {"Sequence", Menu {
                     {"Shot HUD", toggleHUD, nil, hudState}
                 }}
             });
    }
}

\: createMode (Mode;)
{
    return SequenceHUDMinorMode();
}

} // module sequence_hud
