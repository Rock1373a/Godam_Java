#!/usr/bin/env bash
# Run `npx expo run:android` with ANDROID_HOME / JAVA_HOME (see scripts/download-android-sdk.sh).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/_android_toolchain_env.sh"

if [ -z "${ANDROID_HOME:-}" ] || [ ! -x "$ANDROID_HOME/platform-tools/adb" ]; then
  echo "Android SDK not found or adb missing." >&2
  echo "  Install into this repo:  bash $ROOT/scripts/download-android-sdk.sh" >&2
  echo "  Or set:  export ANDROID_HOME=\$HOME/Android/sdk   # Android Studio default" >&2
  exit 1
fi

if [ -z "${JAVA_HOME:-}" ] || [ ! -x "$JAVA_HOME/bin/javac" ]; then
  echo "JAVA_HOME not set and no JDK found (need Java 17+)." >&2
  echo "  sudo apt install -y openjdk-17-jdk-headless" >&2
  exit 1
fi

cd "$ROOT/godam-mobile"

if [ ! -d android ]; then
  echo "No native android/ folder yet. Generating with Expo prebuild..." >&2
  npx expo prebuild --platform android
fi

# expo run:android requires a USB device or a running emulator
if ! adb devices 2>/dev/null | awk 'NR>1 && $2=="device"{ok=1} END{exit ok?0:1}'; then
  echo "" >&2
  echo "No Android device/emulator detected (adb shows nothing in 'device' state)." >&2
  echo "  • Plug in a phone with USB debugging, or start an emulator from Android Studio." >&2
  echo "  • To only compile a debug APK (no install), run:" >&2
  echo "      cd $ROOT/godam-mobile && npm run android:build" >&2
  echo "" >&2
  exit 1
fi

exec npx expo run:android "$@"
