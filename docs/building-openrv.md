# Building Sequence RV (rv + rvio) from source

The upstream OpenRV README is the authoritative, per-release source for
platform prerequisites — read it alongside this page. This page covers the
studio-specific parts.

## 1. Fetch upstream at a pinned release

```bash
SEQ_OPENRV_TAG=<release-tag> bash scripts/get_openrv.sh
```

Pick the tag from the
[OpenRV releases page](https://github.com/AcademySoftwareFoundation/OpenRV/releases)
and record it with the build. Building `main` is fine for evaluation, never
for deployment.

## 2. Platform prerequisites (summary — upstream README is canonical)

- **Linux**: upstream targets Rocky/RHEL-family; you need the usual C++
  toolchain, CMake, Qt (version per upstream release), Python, and a list of
  -devel packages from the upstream README. Build on the oldest OS you
  deploy to.
- **macOS**: Xcode command line tools, Homebrew deps, Qt per upstream README.
- **Windows**: MSYS2-based; follow upstream closely.

## 3. Codecs — read this before the first dailies QuickTime

Commercial RV shipped with licensed codecs. OpenRV builds its own ffmpeg and
**disables some non-free decoders/encoders by default** (the classic symptom:
h.264 `.mov`s from editorial won't decode, or you can't write h.264
dailies).

The upstream build reads environment variables listing non-free codecs to
enable; `scripts/build_openrv.sh` forwards them:

```bash
SEQ_FFMPEG_NON_FREE="aac" bash scripts/build_openrv.sh
```

Which codecs to enable — and whether the studio's licensing position covers
them — is a business decision, not a technical one. Decide it once, write it
down, and bake it into the build. The patent-unencumbered path (EXR
sequences for review, ProRes via other tooling) needs no flags.

## 4. Build

```bash
bash scripts/build_openrv.sh                       # wraps upstream's rvcmds.sh bootstrap
SEQ_APPLY_BRANDING=1 bash scripts/build_openrv.sh  # …with splash/icon replacement
```

First builds take a long time (Qt-sized dependency chain) and disk. If
upstream's entrypoint has changed for your pinned release, the script says so
and defers to the upstream README — build manually, then continue below.

## 5. Bundle the studio kit

```bash
make packages
bash scripts/bundle_release.sh   # default stage: _external/OpenRV/_build/stage/app
```

This copies the `.rvpkg`s into the distribution's `plugins/Packages`,
registers them in the `rvinstall` auto-install list when present, and drops
`seqrv`/`seqrvio` next to the binaries. Archive the stage directory and
that's the deployable:

```bash
tar -C _external/OpenRV/_build/stage -czf sequence-rv-$(cat VERSION)-linux.tar.gz app
```

## 6. Smoke-test checklist

- [ ] `rv` launches; window title says **Sequence RV**; Sequence menu exists
- [ ] `examples/dailies_example.json` loads (fix the media paths first);
      `alt+→` steps shots; HUD shows metadata
- [ ] Notes panel opens (`alt+n`), a note survives session save/reload
- [ ] Annotate a frame → Export Annotated Frames + Report → PNGs + report.html
- [ ] With a show OCIO config wired: console shows `[sequence_ocio]`
      assignments and the image visibly changes
- [ ] `rvio session.rv -o out.mov` renders; codecs you need actually encode
- [ ] Check the console for any `[sequence_*]` warnings — each one names the
      exact property/API that needs a one-line fix if upstream drifted

## Keeping up with upstream

Bump `SEQ_OPENRV_TAG`, rebuild, rerun the smoke-test checklist. The kit
tracks upstream through documented package APIs only — no source patches
except the optional branding asset swap — so version bumps are cheap.
