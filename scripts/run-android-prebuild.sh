#!/usr/bin/env bash
# Generate godam-mobile/android (and ios if you add --platform ios later)
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
exec npx expo prebuild --platform android "$@"
