# Branding assets

The Sequence circle wordmark is the studio identity for Sequence RV.

| File | What it is |
| --- | --- |
| `logo_master.png` | The supplied logo (RGBA, transparent outside the circle) — source of truth for the raster assets |
| `logo.svg` | Vector recreation for print/docs (regenerate rasters after editing it) |
| `icon.png` | 512px square app icon (replaces upstream PNG icons at build time) |
| `splash.png` | Launch splash — dark field with the centered wordmark |
| `icon.ico` | Windows icon (installer, shortcuts, exe) — 16→256px, PNG-compressed |
| `icon.icns` | macOS bundle icon — 32→1024px, PNG-based |

## Regenerating

Everything except the master and the SVG is generated:

```bash
pip install pillow           # only needed for regeneration
python3 scripts/make_brand_assets.py
```

To swap in a new/higher-resolution master (≥1024px will improve the large
icon sizes — the current master is 270px, so 512/1024 variants are upscales,
acceptable for this flat two-tone mark):

```bash
python3 scripts/make_brand_assets.py --source /path/to/new_logo.png
```

## Where the assets get used

- **Build time** — `scripts/apply_branding.py` (on by default via
  `configs/build.env`) replaces upstream splash/icon files in the OpenRV
  source tree, so the compiled `rv` shows the Sequence splash on launch.
- **Installers** — `installers/windows/sequence-rv.iss` embeds `icon.ico`;
  `scripts/make_installer_macos.sh` swaps `icon.icns` into the app bundle.
- **Runtime** — the `sequence_branding` package handles window title/About
  independently, so even an unbranded build identifies itself.
