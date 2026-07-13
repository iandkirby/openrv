# Building Sequence RV (rv + rvio) from source

Studio target platform: **Windows (PC)**. Codec requirements of record:
**EXR sequences, h.264 and h.265 (HEVC) movies** — see
`configs/build.env`, which bakes these into every build.

The upstream OpenRV README is the authoritative, per-release source for
prerequisites — read it alongside this page; this page covers the studio
specifics.

## 1. Fetch upstream at a pinned release

```bash
SEQ_OPENRV_TAG=<release-tag> bash scripts/get_openrv.sh
```

Pick the tag from the
[OpenRV releases page](https://github.com/AcademySoftwareFoundation/OpenRV/releases)
and record it with the build. Building `main` is fine for evaluation, never
for deployment.

## 2. Codecs — the studio decision, wired in

| Need | How it's covered |
| --- | --- |
| **EXR** (plates, comps) | Nothing to do — OpenEXR is core OpenRV, always on. Same for DPX/TIFF/JPEG. |
| **h.264 / h.265 decode** (+ AAC audio) | ffmpeg's native decoders exist but upstream compiles the non-free set out by default. `configs/build.env` opts them back in (`SEQ_FFMPEG_NON_FREE_DECODERS=h264,hevc,aac`), which `scripts/build_openrv.sh` forwards to the upstream build (`RV_FFMPEG_NON_FREE_*_TO_ENABLE`). Cross-check the exact codec-name spelling against the disabled list in your pinned release's ffmpeg cmake if the build logs don't mention them. |
| **h.264 / h.265 encode** (rvio writing movies) | Not a flag — ffmpeg has **no built-in software encoders** for these; they come from libx264/libx265 (GPL) or NVENC, neither in the stock OpenRV build. See below. |

Enabling the non-free decoders means the studio accepts the associated
patent-license posture (the reason upstream ships them off). That decision is
recorded in `configs/build.env` — change it by reviewed commit only.

### Getting h.264/h.265 *encoding* for dailies movies

Recommended path (keeps the OpenRV build stock and the GPL out of it):
render from `rvio` to an intermediate (EXR/TIFF frames), then transcode with
a standalone ffmpeg that has libx264/libx265 — a two-line farm step:

```bat
seqrvio session.rv -o out\dailies.#.tiff
ffmpeg -i out\dailies.%%d.tiff -c:v libx265 -crf 20 -pix_fmt yuv420p dailies.mp4
```

Alternatives if in-rvio encoding becomes a hard requirement:
- Add libx264/libx265 to the ffmpeg the OpenRV build compiles — GPL applies
  to the resulting binary; internal-only use is typically fine, distributing
  it outside the studio is not, and it's build surgery to redo each upstream bump.
- NVENC hardware encoders (`h264_nvenc`/`hevc_nvenc`) — needs NVIDIA SDK
  headers in the ffmpeg build and NVIDIA GPUs wherever rvio runs.

A `seqrvio --transcode` wrapper for the two-step path is an easy later addition.

## 3. Windows build walkthrough

Exact tool versions (Visual Studio edition, Qt, Python, CMake) are dictated
by the pinned upstream release — check its README section for Windows before
installing anything. The shape of it:

1. Install the compiler toolchain upstream specifies (Visual Studio with
   C++ workload), CMake, Python, and Qt (upstream pins the version; the
   open-source Qt installer works).
2. Install **MSYS2** — upstream's Windows build runs from an MSYS2 bash
   shell with a list of MSYS2 packages from their README. Our `scripts/*.sh`
   run in that same shell.
3. From the MSYS2 shell, in this repo:
   ```bash
   SEQ_OPENRV_TAG=<tag> bash scripts/get_openrv.sh
   SEQ_APPLY_BRANDING=1 bash scripts/build_openrv.sh   # sources configs/build.env
   make packages
   bash scripts/bundle_release.sh
   ```
4. The bundled stage directory now contains `rv.exe`, `rvio.exe`, the studio
   `.rvpkg`s, `seqrv.cmd`/`seqrvio.cmd` (plus the bash launchers for MSYS2
   users), and `sequence\` with the studio configs. Zip it and deploy — a
   plain directory on a share works; artists run `seqrv.cmd`.

First builds take a long time (Qt-sized dependency chain) and real disk.
Linux/macOS follow the same steps minus MSYS2; build on the oldest OS you
deploy to.

## 4. Smoke-test checklist

- [ ] `rv` launches; window title says **Sequence RV**; Sequence menu exists
- [ ] **An editorial h.264 `.mov` and an h.265 `.mp4` play with audio** —
      this is the codec flags working; if not, check the build log for the
      ffmpeg configure line and the non-free enable list
- [ ] An EXR sequence plays
- [ ] `examples/dailies_example.json` loads (fix the media paths first);
      `alt+→` steps shots; HUD shows metadata
- [ ] Notes panel opens (`alt+n`), a note survives session save/reload
- [ ] Annotate a frame → Export Annotated Frames + Report → PNGs + report.html
- [ ] With a show OCIO config wired: console shows `[sequence_ocio]`
      assignments and the image visibly changes
- [ ] `rvio session.rv -o out.mov` renders; confirm which encoders exist in
      your build before promising formats to production
- [ ] Check the console for `[sequence_*]` warnings — each names the exact
      property/API needing a one-line fix if upstream drifted

## Keeping up with upstream

Bump `SEQ_OPENRV_TAG`, rebuild, rerun the smoke-test checklist. The kit
tracks upstream through documented package APIs only — no source patches
except the optional branding asset swap — so version bumps are cheap.
