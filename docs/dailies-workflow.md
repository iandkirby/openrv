# Dailies workflow

## Manifest format

A dailies session is a JSON file, one object per item in play order:

```json
{
  "show": "SHOWA",
  "date": "2026-07-13",
  "items": [
    {
      "shot":   "sq010_sh0010",
      "media":  "/shows/SHOWA/sq010/sh0010/comp/sh0010_comp_v012.####.exr",
      "range":  [1001, 1048],
      "artist": "rk",
      "status": "wip",
      "note":   "grade tweak on fg"
    }
  ]
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `media` | yes | Anything RV can open: `####` frame sequences, movies, single frames |
| `shot` | no | Defaults to the media basename; used by HUD, notes, and reports |
| `range` | no | `[in, out]` cut applied to the source; omit to play full length |
| `artist`, `status`, `note` | no | Shown on the HUD, carried into reports |

Manifests are plain JSON precisely so anything can generate them — a shell
script over the filesystem today, an asset database later. The generator you
write is the studio's replacement for "playlist from ShotGrid".

## What loading does

For each item, the loader adds a source, applies the cut range, and writes
the metadata onto the source group (`sequence_review.*` properties). All
sources are wired into a sequence node, shot boundaries get frame marks, and
the state is stored on the sequence node — so `alt+→`/`alt+←` navigation
works even after saving and reopening the `.rv` session.

Everything the kit writes lives in ordinary RV properties, which means a
saved session file is the complete record of the review: media, cuts,
metadata, annotations, and notes.

## Notes and statuses

Notes are per-shot, timestamped, attributed to `$USER`, and carry one of:
`note`, `approved`, `cbb`, `fix`. Exports:

- **Sequence → Export Notes (JSON)** — stable interchange payload
  (`{"show", "generated", "shots": {shot: [notes]}}`)
- **Sequence → Export Notes (CSV)** — for spreadsheets
- The HTML report (below) includes notes next to each annotated frame

## Review report

**Sequence → Export Annotated Frames + Report…** does, in order:

1. Saves the session (with paint strokes) to a temp `.rv` file.
2. Finds annotated frames (falls back to marked frames on older builds).
3. Renders exactly those frames through `rvio` into the chosen directory.
4. Writes `report.html` (standalone, printable → PDF) and `report.json`
   pairing every frame with its shot and notes.

The directory is self-contained — zip it and send it, or drop it on the
review share.
