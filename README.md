# Sequence RV — The Sequence Group build of OpenRV

Self-hosted `rv` and `rvio` for **The Sequence Group**, built on
[Academy Software Foundation OpenRV](https://github.com/AcademySoftwareFoundation/OpenRV).

This repo exists so the studio keeps a fully working review player and frame
renderer **after the ShotGrid subscription (and its bundled commercial RV)
ends** — no license keys, no phone-home, and our own review tooling baked in.

It is deliberately a *studio layer*, not a fork: upstream OpenRV is fetched at
a pinned release and built as-is, then our packages, color config, branding,
and launchers are bundled into the distribution. Staying unforked means
upstream fixes are one `SEQ_OPENRV_TAG` bump away.

## What's in the box

| Piece | What it does |
| --- | --- |
| `packages/sequence_dailies` | Builds a dailies session from a JSON manifest: sources, cut ranges, shot metadata, marked shot boundaries, next/prev-shot hotkeys. |
| `packages/sequence_hud` | Heads-up overlay (Mu) showing shot, artist, status, and media name for the current source. |
| `packages/sequence_notes` | Dockable notes panel: per-shot notes with author/status, stored in the session file, exportable to JSON/CSV. |
| `packages/sequence_annotation_export` | Renders annotated frames through `rvio` and writes a standalone HTML review report + notes JSON. |
| `packages/sequence_ocio` | Per-show OCIO config resolution and per-media colorspace assignment from `configs/ocio_rules.json`. |
| `packages/sequence_branding` | Window title, About box, startup feedback — makes it *Sequence RV*. |
| `bin/seqrv`, `bin/seqrvio` | Studio launchers: set show/OCIO/support-path environment, then exec `rv` / `rvio`. |
| `scripts/` | Fetch upstream at a pinned tag, build, apply branding, build `.rvpkg`s, bundle a release. |

## Quickstart A — add the kit to an existing OpenRV install

Use this while you still have RV/OpenRV installed and just want the studio
tooling:

```bash
make packages                      # builds dist/*.rvpkg
bash scripts/install_packages.sh   # installs into ~/.rv via rvpkg
rv                                 # Sequence menu appears
```

`install_packages.sh` needs the `rvpkg` tool that ships next to `rv`
(it looks at `$SEQ_RVPKG`, `$PATH`, then `$RV_HOME/bin`).

## Quickstart B — build the whole player from source

```bash
bash scripts/get_openrv.sh         # clone upstream into _external/OpenRV (pin with SEQ_OPENRV_TAG)
bash scripts/build_openrv.sh       # wraps upstream's build (see docs/building-openrv.md for deps)
make packages
bash scripts/bundle_release.sh     # copies our .rvpkgs into the built distribution
```

The result is a distributable `rv` + `rvio` with the Sequence kit inside.
Platform prerequisites and the ffmpeg codec story (important — see below) are
in [docs/building-openrv.md](docs/building-openrv.md).

> **Codec caveat when leaving ShotGrid RV:** the commercial RV shipped with
> licensed codecs. OpenRV builds ffmpeg with some non-free decoders/encoders
> disabled by default. If your dailies rely on them, you must opt in at build
> time (see `docs/building-openrv.md`) — enabling them is the studio's own
> licensing call.

## Launching

```bash
bin/seqrv --show SHOWA --dailies /path/to/dailies_2026-07-13.json
bin/seqrvio session.rv -o review.mov
```

`seqrv` exports `SEQ_SHOW`, `SEQ_DAILIES_MANIFEST`, `SEQ_KIT_ROOT`, resolves
the show's OCIO config, and execs the real `rv` (found via `--rv`,
`$SEQ_RV_BIN`, or `$PATH`).

## Dailies manifest

```json
{
  "show": "SHOWA",
  "date": "2026-07-13",
  "items": [
    {
      "shot": "sq010_sh0010",
      "media": "/shows/SHOWA/sq010/sh0010/comp/sh0010_comp_v012.####.exr",
      "range": [1001, 1048],
      "artist": "rk",
      "status": "wip",
      "note": "grade tweak on fg"
    }
  ]
}
```

Load it with **Sequence → Load Dailies Manifest…**, pass it to `seqrv
--dailies`, or set `$SEQ_DAILIES_MANIFEST`. Full format in
[docs/dailies-workflow.md](docs/dailies-workflow.md).

## Default hotkeys

| Key | Action |
| --- | --- |
| `alt+→` / `alt+←` | Next / previous shot in the dailies sequence |
| `alt+h` | Toggle the shot HUD |
| `alt+n` | Toggle the notes panel |

## Repository layout

```
packages/     one directory per RV package (source of the .rvpkg files)
configs/      studio config (OCIO rules)
ocio/         placeholder OCIO config — replace with the studio ACES config
examples/     sample dailies manifest
scripts/      fetch/build/bundle/package tooling
bin/          seqrv & seqrvio launchers
docs/         getting started, dailies, color, building
tests/        pure-Python unit tests (no RV required)
```

## Development

```bash
make lint      # byte-compile + PACKAGE manifest validation
make test      # unit tests for the RV-independent core modules
make packages  # build dist/*.rvpkg
make dev       # install packages into ./rv-support for RV_SUPPORT_PATH testing
```

Each package splits RV-facing glue (`*_core.py`-free) from pure logic
(`*_core.py`) so the logic is unit-testable without an RV runtime. CI runs
lint + tests and attaches the built `.rvpkg`s to every run; tagging `v*`
publishes a GitHub release.

**A note on verification:** everything here that talks to RV uses the
documented OpenRV Python/Mu APIs, but this repo was authored without a running
RV build to test against. The first smoke-test against your built OpenRV may
surface small API drift (exact property or event names) — each package logs
`[sequence_*]` lines to the console to make that easy to spot. Core logic is
covered by real unit tests.

## Roadmap

- [ ] CI job that builds full OpenRV per platform (needs beefier runners)
- [ ] Tracker-agnostic notes hand-off (JSON is already the interchange)
- [ ] Streaming/remote-review recipe
- [ ] Windows launcher scripts

---
Contact: software@thesequencegroup.com · Licensed Apache-2.0 (same family as upstream OpenRV).
