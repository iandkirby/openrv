# Branding assets

Runtime branding (window title, About box, startup message) is handled by the
`sequence_branding` package and needs nothing from this directory.

Compile-time branding is asset replacement in the upstream source tree,
applied by `scripts/apply_branding.py` before building (or automatically with
`SEQ_APPLY_BRANDING=1 scripts/build_openrv.sh`). Drop these files here:

| File | Replaces | Recommended |
| --- | --- | --- |
| `splash.png` | upstream splash screen image(s) | match upstream's dimensions (check the file it's replacing — the script prints the paths and keeps `.orig` backups) |
| `icon.png` | application icon image(s) | square PNG, largest upstream size |

`logo.svg` is the studio wordmark source — export `splash.png`/`icon.png`
from it at whatever sizes the pinned upstream release uses.

The script matches targets by filename pattern (`*splash*`, `*rv_icon*` etc.)
rather than hard-coded paths, prints exactly what it will replace, and backs
up originals as `<name>.orig`, so it is safe to re-run and easy to revert.
