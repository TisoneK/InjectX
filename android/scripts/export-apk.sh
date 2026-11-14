#!/usr/bin/env bash
# Build the debug APK, archive it under android/dist/ with a version+commit
# name (so builds are never overwritten / lost), and copy the latest to the
# Desktop. The dist/ archive is git-tracked — that's our debug-APK history.
set -euo pipefail

cd "$(dirname "$0")/.."   # -> android/
: "${JAVA_HOME:=$HOME/.local/toolchain/jdk-17.0.21+9/Contents/Home}"
export JAVA_HOME

./gradlew :app:assembleDebug --console=plain

APK="app/build/outputs/apk/debug/app-debug.apk"
[ -f "$APK" ] || { echo "no APK at $APK" >&2; exit 1; }

# Re-sign with v1 + v2 + v3 (AGP drops v1 at minSdk >= 24; some OEM installers
# reject v2-only APKs with "package appears invalid"). --min-sdk-version 21
# forces apksigner to emit the v1 JAR signature.
APKSIGNER="$HOME/.local/android-sdk/build-tools/34.0.0/apksigner"
KS="$HOME/.android/debug.keystore"
"$APKSIGNER" sign --ks "$KS" --ks-pass pass:android \
  --ks-key-alias androiddebugkey --key-pass pass:android \
  --min-sdk-version 21 \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  "$APK"

VER="$(sed -n 's/.*versionName *= *"\([^"]*\)".*/\1/p' app/build.gradle.kts | head -n1)"
# Name the archive by the last commit that changed the APK's CODE (app/core),
# so doc/ledger-only commits don't spawn duplicate 13MB blobs.
SHA="$(git log -1 --format=%h -- app core 2>/dev/null || echo nogit)"
DIRTY=""
git diff --quiet -- app core 2>/dev/null || DIRTY="-dirty"
NAME="injectx-debug-v${VER}-${SHA}${DIRTY}.apk"

mkdir -p dist
DESKTOP="$HOME/Desktop/injectx-debug.apk"
cp "$APK" "$DESKTOP"
echo ""
if [ -f "dist/$NAME" ] && [ -z "$DIRTY" ]; then
  echo "archive  : android/dist/$NAME (up to date — app unchanged, not duplicated)"
else
  cp "$APK" "dist/$NAME"
  echo "archived : android/dist/$NAME"
fi
echo "desktop  : $DESKTOP (latest)"
echo "signed   :"
"$APKSIGNER" verify --min-sdk-version 19 -v "$APK" 2>/dev/null | grep -E 'Verified using' || true
