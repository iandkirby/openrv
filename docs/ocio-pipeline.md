# Color pipeline (OCIO)

## How color is decided

1. **Which config?** `$OCIO` wins if set. Otherwise the show
   (`$SEQ_SHOW`, or detected from a `/shows/<name>/` path segment) is looked
   up in `config_by_show` in the rules file; `default` is the fallback.
   The `seqrv`/`seqrvio` launchers resolve this *before* RV starts so child
   processes (and farm renders) inherit the same config; the `sequence_ocio`
   package repeats the resolution inside RV as a fallback.
2. **Which input colorspace?** The first `file_rules` regex matching the
   media path assigns the source's input colorspace; the source's linearize
   pipeline becomes an `OCIOFile` node converting into `working_colorspace`.
3. **Which display transform?** Display pipelines switch to `OCIODisplay`
   with the configured `display`/`view`.

If no config resolves, the kit deliberately leaves RV's built-in color
management untouched — media never silently renders through a wrong config.
Set `SEQ_OCIO_DISABLE=1` to bypass everything for a session.

## Rules file

`configs/ocio_rules.json` (override location with `$SEQ_OCIO_RULES`):

```json
{
  "config_by_show": {
    "default": "${SEQ_KIT_ROOT}/ocio/config.ocio",
    "SHOWA":   "/shows/SHOWA/ocio/config.ocio"
  },
  "working_colorspace": "ACEScg",
  "file_rules": [
    { "pattern": "\\.exr$",       "colorspace": "ACEScg" },
    { "pattern": "\\.(mov|mp4)$", "colorspace": "sRGB - Texture" }
  ],
  "display": "sRGB - Display",
  "view": "ACES 1.0 - SDR Video"
}
```

Every colorspace/display/view name must exist in the show's config. Rules are
evaluated top-down, first match wins, matching is case-insensitive
`re.search` on the full media path — so pipeline-step rules like
`"/comp/.*\\.exr$"` work too.

## Per-show setup checklist

1. Put the show's OCIO config on the server (ACES configs:
   [OpenColorIO-Config-ACES](https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES)).
2. Add the show to `config_by_show`.
3. Update `file_rules` / `display` / `view` if the show's naming differs.
4. Verify in RV: console shows `[sequence_ocio]` lines naming each
   assignment, e.g. `plate.1001.exr: ACEScg -> ACEScg`.

## Verification note

The OCIO *node property names* (`ocio.inColorSpace`,
`ocio_color.outColorSpace`, `ocio_display.display`, …) follow OpenRV's
bundled `ocio_source_setup` package. On your first smoke-test against a
freshly built OpenRV, confirm the assignments visibly change the image and
check the console for `[sequence_ocio]` warnings — if upstream renamed
anything between releases, this package is the single place to adjust
(`packages/sequence_ocio/sequence_ocio.py`, `_setupSource` /
`onSessionInitialized`).
