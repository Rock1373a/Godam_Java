#!/usr/bin/env bash
# Start a headless Android Virtual Device using the repo SDK (tools/android-sdk).
# Creates AVD "godam_avd" if missing. Suitable when /dev/kvm is unavailable (slow).
#
# Usage from repo root:
#   bash scripts/start-android-emulator.sh
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/_android_toolchain_env.sh"
SDK="${ANDROID_HOME:?ANDROID_HOME not set}"
EMU="$SDK/emulator/emulator"
ADB="$SDK/platform-tools/adb"
AVDM="$SDK/cmdline-tools/latest/bin/avdmanager"
SM="$SDK/cmdline-tools/latest/bin/sdkmanager"
AVD_NAME="${GODAM_AVD_NAME:-godam_avd}"
PKG_SYSIMG="system-images;android-35;google_apis;x86_64"

if [[ ! -x "$EMU" ]]; then
  echo "Emulator binary missing; installing package 'emulator' into $SDK …" >&2
  export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
  set +o pipefail
  yes | "$SM" --sdk_root="$SDK" --licenses >/dev/null 2>&1 || true
  yes | "$SM" --sdk_root="$SDK" "emulator" || true
  set -o pipefail
fi
if [[ ! -x "$EMU" ]]; then
  echo "Still no emulator at $EMU — run: $SM --sdk_root=$SDK emulator" >&2
  exit 1
fi

if ! "$AVDM" list avd 2>/dev/null | grep -qF "Name: ${AVD_NAME}"; then
  echo "Creating AVD ${AVD_NAME} (${PKG_SYSIMG}) …" >&2
  echo no | "$AVDM" create avd -n "$AVD_NAME" -k "$PKG_SYSIMG" --force
fi

if "$ADB" devices 2>/dev/null | grep -qE '^emulator-[0-9]+[[:space:]]+device$'; then
  echo "An emulator is already running:" >&2
  "$ADB" devices
  exit 0
fi

echo "Starting ${AVD_NAME} (headless, software GPU, no KVM) …" >&2
LOG="${GODAM_EMULATOR_LOG:-$ROOT/emulator-boot.log}"
nohup "$EMU" -avd "$AVD_NAME" -no-window -no-audio -gpu swiftshader_indirect -accel off \
  -no-snapshot-save >>"$LOG" 2>&1 &
echo "PID $! — tail log: $LOG" >&2

for _ in $(seq 1 180); do
  if "$ADB" devices 2>/dev/null | grep -qE '^emulator-[0-9]+[[:space:]]+device$'; then
    "$ADB" devices
    exit 0
  fi
  sleep 1
done
echo "Timed out waiting for emulator in adb device state. See $LOG" >&2
exit 1
