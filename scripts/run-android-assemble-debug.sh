#!/usr/bin/env bash
# Build debug APK only (no device/emulator). Output: android/app/build/outputs/apk/debug/app-debug.apk
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/_android_toolchain_env.sh"

if [ -z "${ANDROID_HOME:-}" ] || [ ! -x "$ANDROID_HOME/platform-tools/adb" ]; then
  echo "Android SDK not found. Run: bash $ROOT/scripts/download-android-sdk.sh" >&2
  exit 1
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "$JAVA_HOME/bin/javac" ]; then
  echo "JDK not found. Install: sudo apt install -y openjdk-17-jdk-headless" >&2
  exit 1
fi

cd "$ROOT/godam-mobile"
if [ ! -d android ]; then
  echo "Generating android/ with Expo prebuild..." >&2
  npx expo prebuild --platform android
fi

cd android
./gradlew assembleDebug "$@"

APK="$ROOT/godam-mobile/android/app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo "BUILD OK — install this file on a device (or adb install -r):"
echo "  $APK"
echo ""
