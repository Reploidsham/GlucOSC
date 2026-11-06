#!/usr/bin/env bash
# One command: build the newest GlucOSC AppImage and check that it really is the newest.
#
#     bash build-test-appimage.sh
#
# What it does, in order:
#   1. Makes the hash-locked package list if it doesn't exist yet (needs internet, one time).
#   2. Builds dist/GlucOSC-x86_64.AppImage with packaging/build_appimage.sh.
#   3. Runs the finished AppImage with --self-check, which tests the code inside it
#      (10 languages, rotate mode, BG_Words, Qt bundled).
#   4. Writes dist/BUILD-INFO.txt (time, source fingerprint, AppImage fingerprint).
#   5. Prints NEWEST BUILD OK with the file to use, or says exactly what failed.
# For testing only. For a public release use the GitHub workflow (docs/RELEASING.md).
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
ROOT="$(pwd)"
LOCK="packaging/requirements-build.txt"
APPIMAGE="dist/GlucOSC-x86_64.AppImage"
SRC="src/glucose_osc_bridge.py"

say() { printf '\n== %s\n' "$1"; }
fail() { printf '\nFAILED: %s\n' "$1" >&2; exit 1; }

for tool in python3 curl sha256sum; do
  command -v "$tool" >/dev/null 2>&1 || fail "'$tool' is not installed. Install it and run this again."
done
python3 -c 'import venv' 2>/dev/null || fail "Python 'venv' is missing. On Debian/Ubuntu: sudo apt install python3-venv"

say "Source being built"
SRC_SHA="$(sha256sum "$SRC" | cut -d' ' -f1)"
echo "$SRC  sha256 $SRC_SHA"

if [ ! -f "$LOCK" ]; then
  say "Making the locked package list (one time, needs internet)"
  python3 packaging/lock_deps.py || fail "Could not lock the build tools. Send me the text above."
else
  echo "Using the existing $LOCK"
fi

say "Building the AppImage (a few minutes)"
START="$(date +%s)"
bash packaging/build_appimage.sh || fail "The build stopped. Send me the last 20 lines above."
[ -f "$APPIMAGE" ] || fail "Build said it finished, but $APPIMAGE is missing."
MTIME="$(stat -c %Y "$APPIMAGE")"
[ "$MTIME" -ge "$START" ] || fail "$APPIMAGE is older than this run, so it is NOT a new build."

say "Checking the code inside the finished AppImage"
CHECK_OUT="$(APPIMAGE_EXTRACT_AND_RUN=1 QT_QPA_PLATFORM=offscreen "./$APPIMAGE" --self-check 2>&1)"
CHECK_RC=$?
echo "$CHECK_OUT"
[ "$CHECK_RC" -eq 0 ] || fail "The AppImage started but is missing something (see FAIL lines above), so don't use it."
echo "$CHECK_OUT" | grep -q "GlucOSC build self-check" || fail "The AppImage did not answer the self-check, so it is not the newest code."

say "Writing dist/BUILD-INFO.txt"
APP_SHA="$(sha256sum "$APPIMAGE" | cut -d' ' -f1)"
{
  echo "Built:      $(date -u '+%Y-%m-%d %H:%M:%S') UTC"
  echo "Source:     $SRC"
  echo "Source sha: $SRC_SHA"
  echo "AppImage:   $APPIMAGE"
  echo "App sha:    $APP_SHA"
  echo "Self-check: passed"
  echo "$CHECK_OUT" | sed -n 's/^  languages: /Languages:  /p'
} > dist/BUILD-INFO.txt
cat dist/BUILD-INFO.txt

OTHERS="$(find "$ROOT" -maxdepth 2 -name '*.AppImage' ! -path "$ROOT/$APPIMAGE" 2>/dev/null)"
if [ -n "$OTHERS" ]; then
  say "Older AppImage files found (don't use these)"
  echo "$OTHERS"
fi

printf '\n======================================================\n'
printf ' NEWEST BUILD OK\n'
printf ' Use this file:  %s/%s\n' "$ROOT" "$APPIMAGE"
printf ' (make it runnable once:  chmod +x %s)\n' "$APPIMAGE"
printf '======================================================\n'
