# Getting started

Two ways in, depending on where you are in the ShotGrid exit:

## Still have an RV/OpenRV install? Add the kit to it

```bash
make packages
bash scripts/install_packages.sh        # installs into ~/.rv via rvpkg
```

Launch `rv` — a **Sequence** menu appears with the dailies loader, notes
panel, HUD toggle, exports, and OCIO controls. To install for a shared
support area instead of `~/.rv`:

```bash
bash scripts/install_packages.sh /studio/tools/rv-support
export RV_SUPPORT_PATH=/studio/tools/rv-support
```

## Building your own player (the post-ShotGrid state)

See [building-openrv.md](building-openrv.md). Short version:

```bash
SEQ_OPENRV_TAG=<release-tag> bash scripts/get_openrv.sh
bash scripts/build_openrv.sh
make packages
bash scripts/bundle_release.sh
```

## Daily use

```bash
bin/seqrv --show SHOWA --dailies /shows/SHOWA/dailies/2026-07-13.json
```

| Key | Action |
| --- | --- |
| `alt+→` / `alt+←` | next / previous shot |
| `alt+h` | toggle shot HUD |
| `alt+n` | toggle notes panel |

Review flow:

1. Load the dailies manifest (menu, `--dailies`, or `$SEQ_DAILIES_MANIFEST`).
2. Step shots with `alt+→`; the HUD shows shot/artist/status.
3. Annotate frames with RV's annotation tools; add notes in the panel
   (`alt+n`) with a status (`note` / `approved` / `cbb` / `fix`).
4. **Sequence → Export Annotated Frames + Report…** writes `report.html`,
   `report.json`, and the annotated PNGs to a folder you pick. Notes alone
   can also be exported as JSON/CSV.

Notes live inside the `.rv` session file, so saving the session preserves
the whole review.

## Environment reference

| Variable | Meaning |
| --- | --- |
| `SEQ_SHOW` | Current show code; drives OCIO config resolution and titles |
| `SEQ_DAILIES_MANIFEST` | Manifest auto-loaded at startup |
| `SEQ_OCIO_RULES` | Override path to the OCIO rules JSON |
| `SEQ_OCIO_DISABLE=1` | Skip all OCIO setup for a session |
| `SEQ_KIT_ROOT` | Kit root (set by launchers; used to find default configs) |
| `SEQ_RV_BIN` / `SEQ_RVIO_BIN` / `SEQ_RVPKG` | Explicit binary locations |
