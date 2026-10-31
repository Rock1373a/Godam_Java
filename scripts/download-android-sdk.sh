#!/usr/bin/env bash
# Download Google's Android command-line tools + core packages into tools/android-sdk/
# Requires: curl, unzip, openjdk-17 (sudo apt install -y curl unzip openjdk-17-jdk-headless)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SDK_ROOT="${ANDROID_SDK_ROOT:-$ROOT/tools/android-sdk}"
JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
export JAVA_HOME

ZIP_VER="${ANDROID_CMDLINE_TOOLS_ZIP:-commandlinetools-linux-14742923_latest.zip}"
URL="https://dl.google.com/android/repository/${ZIP_VER}"

mkdir -p "$SDK_ROOT"
cd "$SDK_ROOT"

if [ ! -x "$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" ]; then
  echo "Downloading $URL"
  curl -fL -o "$ZIP_VER" "$URL"
  unzip -q -o "$ZIP_VER"
  rm -f "$ZIP_VER"
  mkdir -p cmdline-tools/latest
  shopt -s dotglob
  if [ -d cmdline-tools ] && [ ! -d cmdline-tools/latest/bin ]; then
    mv cmdline-tools/* cmdline-tools/latest/
  fi
  shopt -u dotglob
fi

if [ ! -x "$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" ]; then
  echo "sdkmanager not found under $SDK_ROOT/cmdline-tools/latest/bin" >&2
  exit 1
fi

echo "Accepting licenses and installing platform-tools, Android 35 platform, build-tools 35.0.0 ..."
yes | "$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK_ROOT" --licenses >/dev/null
# Avoid SIGPIPE failing the script when sdkmanager closes stdin early
set +o pipefail
yes | "$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK_ROOT" \
  "platform-tools" \
  "platforms;android-35" \
  "build-tools;35.0.0" || true
set -o pipefail

echo ""
echo "Done. Use in this shell:"
echo "  export ANDROID_HOME=\"$SDK_ROOT\""
echo "  export ANDROID_SDK_ROOT=\"$SDK_ROOT\""
echo "  export PATH=\"\$PATH:\$ANDROID_HOME/cmdline-tools/latest/bin:\$ANDROID_HOME/platform-tools\""
echo ""
echo "Or from godam-mobile (scripts set ANDROID_HOME / JAVA_HOME for you):"
echo "  npm run android:build   # debug APK, no phone/emulator required"
echo "  npm run android         # install on a USB device or running emulator"
