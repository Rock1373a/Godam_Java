#!/usr/bin/env bash
# Shared by run-expo-android.sh, run-android-assemble-debug.sh, run-gradle-assemble-release.sh
# Usage: ROOT=/path/to/GoDaam source scripts/_android_toolchain_env.sh
if [ -z "${ROOT:-}" ]; then
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
fi
DEFAULT_SDK="$ROOT/tools/android-sdk"

if [ -z "${ANDROID_HOME:-}" ] || [ ! -x "${ANDROID_HOME}/platform-tools/adb" ]; then
  if [ -x "$DEFAULT_SDK/platform-tools/adb" ]; then
    export ANDROID_HOME="$DEFAULT_SDK"
  fi
fi
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"

if [ -z "${JAVA_HOME:-}" ]; then
  for j in /usr/lib/jvm/java-17-openjdk-amd64 /usr/lib/jvm/java-17-openjdk /usr/lib/jvm/java-21-openjdk-amd64 /usr/lib/jvm/default-java; do
    if [ -x "$j/bin/javac" ]; then
      export JAVA_HOME="$j"
      break
    fi
  done
fi

if [ -n "${ANDROID_HOME:-}" ]; then
  export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:${PATH}"
fi
