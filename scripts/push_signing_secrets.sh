#!/usr/bin/env bash
# Copyright (c) 2026 The Sequence Group.
#
# One-shot: push everything CI needs to sign + notarize the macOS build to
# GitHub as repo secrets. Run this ON YOUR MAC. Your private key is exported
# locally and uploaded straight to GitHub through your own `gh` login — it is
# never printed and never leaves your machine except to GitHub's secret store.
#
#   ./scripts/push_signing_secrets.sh
#
# You need, once:
#   * gh installed + logged in         (brew install gh ; gh auth login)
#   * a valid Developer ID identity    (security find-identity -v -p codesigning)
#   * an app-specific password         (appleid.apple.com -> App-Specific Passwords)

set -euo pipefail

REPO="iandkirby/openrv"
TEAM_ID="2TD5593W26"
APPLE_ID="ian@thesequencegroup.com"

say() { printf '\n\033[1m>> %s\033[0m\n' "$*"; }

# ---- preflight -------------------------------------------------------------
command -v gh >/dev/null || { echo "Install GitHub CLI first: brew install gh"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Log in first: gh auth login"; exit 1; }
security find-identity -v -p codesigning | grep -q "$TEAM_ID" \
  || { echo "No valid Developer ID identity for team $TEAM_ID found."; exit 1; }

WORK="$(mktemp -d /tmp/seq-secrets.XXXXXX)"
trap 'rm -f "$WORK"/*.p12 2>/dev/null; rmdir "$WORK" 2>/dev/null || true' EXIT
P12="$WORK/cert.p12"

# ---- 1. export the signing identity to a password-protected .p12 -----------
say "Exporting your Developer ID identity to a .p12"
echo "Pick ANY password to protect the .p12 (you won't need to remember it —"
echo "it's stored alongside as a secret so CI can open the file):"
read -rs -p "  new .p12 password: " P12PW; echo
[ -n "$P12PW" ] || { echo "empty password, aborting"; exit 1; }

if ! security export -t identities -f pkcs12 -P "$P12PW" -o "$P12" 2>/dev/null; then
  cat >&2 <<EOF

ERROR: macOS would not export the private key.
This happens when the key is non-exportable or lives only in the System
keychain. Fix (2 min), then re-run this script:
  1. Keychain Access -> Certificate Assistant -> Request a Certificate from a
     Certificate Authority (save to disk) -- this makes the key in your LOGIN
     keychain, exportable.
  2. Upload that CSR at developer.apple.com -> Certificates -> Developer ID
     Application, download the cert, double-click to install.
Or skip GitHub entirely and use scripts/../sign_and_notarize.sh (local signing,
no export needed).
EOF
  exit 1
fi

# ---- 2. app-specific password for notarization -----------------------------
say "App-specific password for notarization"
echo "From appleid.apple.com -> Sign-In and Security -> App-Specific Passwords."
echo "Format looks like: abcd-efgh-ijkl-mnop"
read -rs -p "  app-specific password: " APW; echo
[ -n "$APW" ] || { echo "empty password, aborting"; exit 1; }

# ---- 3. push all secrets via your gh login ---------------------------------
say "Pushing secrets to $REPO (through your gh login; values are not printed)"
base64 < "$P12"          | gh secret set MACOS_CERT_P12_BASE64 --repo "$REPO"
printf '%s' "$P12PW"     | gh secret set MACOS_CERT_PASSWORD   --repo "$REPO"
printf '%s' "$APW"       | gh secret set MACOS_NOTARY_APP_PW   --repo "$REPO"
printf '%s' "$APPLE_ID"  | gh secret set MACOS_NOTARY_APPLE_ID --repo "$REPO"
printf '%s' "$TEAM_ID"   | gh secret set MACOS_NOTARY_TEAM_ID  --repo "$REPO"

# scrub the .p12 immediately
rm -f "$P12"

say "Done. Secrets now set on $REPO:"
gh secret list --repo "$REPO" | grep -E "MACOS_" || true
echo
echo "Next build (build_macos) will come out signed + notarized automatically."
