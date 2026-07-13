# Sequence RV (The Sequence Group studio layer on OpenRV)

Studio kit that wraps upstream AcademySoftwareFoundation/OpenRV: RV packages
under `packages/`, build/bundle tooling under `scripts/`, launchers in `bin/`.
Upstream source is *not* vendored — `scripts/get_openrv.sh` clones it into
`_external/OpenRV` (gitignored).

## Commands

- `make lint` — byte-compile + validate every `packages/*/PACKAGE` manifest
- `make test` — `unittest discover -s tests` (pure Python, no RV needed)
- `make packages` — build `dist/*.rvpkg`
- `make dev` — install built packages into `./rv-support`

## Conventions

- Each package dir builds into one `.rvpkg` (zip of `PACKAGE` + mode files).
- RV-facing code lives in `<pkg>.py` / `<pkg>.mu`; anything unit-testable
  lives in `<pkg>_core.py` with **no `rv` imports** — tests import the core
  modules directly.
- Module filenames must stay globally unique: installed packages flatten into
  a single `Python/` directory. Prefix everything `sequence_`.
- Custom node properties use components `sequence_review`, `sequence_notes`,
  `sequence_dailies` — keep that namespacing.
- Handlers bound to shared RV events (`frame-changed`,
  `source-group-complete`, `session-initialized`, …) must call
  `event.reject()` so other modes still receive the event.
- RV API calls that are version-sensitive are wrapped in try/except and log
  with a `[sequence_<pkg>]` prefix; keep doing that — this code is written
  against documented OpenRV APIs but not continuously tested inside RV.
- Qt: import PySide6 first, fall back to PySide2 (OpenRV moved Qt5→Qt6).
- Studio build decisions of record (target platform: Windows; ffmpeg codec
  opt-ins: h264/hevc/aac decode) live in `configs/build.env`, sourced by
  `scripts/build_openrv.sh`. Change via reviewed commit only.
- Launchers exist in pairs: bash (`bin/seqrv`) and Windows cmd
  (`bin/seqrv.cmd`) — keep behavior in sync; shared OCIO resolution lives in
  `scripts/resolve_ocio.py`.
