# OCIO configs

`config.ocio` here is a **placeholder** — a minimal OCIO v2 config (linear +
sRGB + raw) so the kit functions before the studio color pipeline lands. Do
not grade a show through it.

For production:

1. Grab an ACES config (e.g. from
   [OpenColorIO-Config-ACES releases](https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES/releases))
   or author a show config.
2. Put it on the server (e.g. `/shows/SHOWA/ocio/config.ocio`).
3. Map it in `configs/ocio_rules.json` under `config_by_show`, and update
   `file_rules` / `display` / `view` to names that exist in that config
   (e.g. `ACEScg`, `sRGB - Display`, `ACES 1.0 - SDR Video`).

The `seqrv`/`seqrvio` launchers and the `sequence_ocio` package both resolve
`$OCIO` from those rules — launcher first (so child processes inherit it),
package as fallback. An explicitly set `$OCIO` always wins.
