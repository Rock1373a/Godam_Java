#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/_android_toolchain_env.sh"

if [ -z "${ANDROID_HOME:-}" ]; then
  echo "Set ANDROID_HOME or run: bash $ROOT/scripts/download-android-sdk.sh" >&2
  exit 1
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "$JAVA_HOME/bin/javac" ]; then
  echo "JDK not found. Install: sudo apt install -y openjdk-17-jdk-headless" >&2
  exit 1
fi

if [ ! -d "$ROOT/godam-mobile/android" ]; then
  echo "No android/ folder. From godam-mobile run: npx expo prebuild --platform android" >&2
  exit 1
fi

cd "$ROOT/godam-mobile/android"
exec ./gradlew assembleRelease "$@"
