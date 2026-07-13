# Building the downloadable installers

Both installers wrap a **built + bundled** distribution, so the order is
always: build OpenRV on that platform → `make packages` →
`scripts/bundle_release.sh` → installer script. Branding (Sequence splash on
launch, icons) is applied during the build step automatically
(`SEQ_APPLY_BRANDING=1` is the default in `configs/build.env`).

## Windows — `SequenceRV-<version>-Setup.exe`

On the Windows build machine, with [Inno Setup 6](https://jrsoftware.org/isinfo.php)
installed:

```bat
scripts\make_installer_windows.cmd
```

The installer:
- installs to `Program Files\Sequence RV` with the Sequence icon everywhere
- Start-menu (and optional desktop) shortcuts launching `seqrv.cmd`, so
  artists get the studio environment (OCIO, show context) by default —
  plus a "plain rv" shortcut
- associates `.rv` session files
- upgrades in place (stable AppId) and uninstalls cleanly

## macOS — `SequenceRV-<version>.dmg`

On the Mac build machine:

```bash
bash scripts/make_installer_macos.sh            # finds the staged .app
bash scripts/make_installer_macos.sh /path/to/RV.app
```

The script rebrands the app (name → **Sequence RV**, Sequence `.icns`),
re-signs it, and produces a standard drag-to-Applications DMG.

**Signing:** by default it ad-hoc signs, which is fine for deployment inside
the studio (file share, MDM). Apps *downloaded* by artists over the internet
will hit Gatekeeper unless signed with a Developer ID and notarized — set
`SEQ_CODESIGN_ID="Developer ID Application: …"` if/when the studio has one.

## Making them downloadable

Attach the installers to a GitHub release so there's one canonical download
URL per version:

```bash
git tag v0.1.0 && git push origin v0.1.0        # CI publishes the .rvpkgs
gh release upload v0.1.0 dist/SequenceRV-0.1.0-Setup.exe dist/SequenceRV-0.1.0.dmg
```

(CI builds and attaches the `.rvpkg` files automatically on tags; the
platform installers are uploaded from the build machines because compiling
OpenRV needs real Windows/macOS hardware and hours of CPU.)

## Splash on launch

The launch splash is a compile-time image in upstream OpenRV, replaced by
`scripts/apply_branding.py` before building — the first branded build shows
the Sequence circle on a dark card at startup (`branding/splash.png`). If a
new upstream release moves its splash assets, the script says what it did
(and keeps `.orig` backups); check its output on version bumps.
