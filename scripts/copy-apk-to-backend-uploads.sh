#!/usr/bin/env bash
# Copy release APK to backend/uploads/mobile/GoDam.apk (served via GET /api/admin/mobile-app/apk when admin).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/godam-mobile/android/app/build/outputs/apk/release/app-release.apk"
DEST_DIR="$ROOT/backend/uploads/mobile"
DEST="$DEST_DIR/GoDam.apk"

if [ ! -f "$SRC" ]; then
  echo "Release APK not found. Build first:" >&2
  echo "  cd $ROOT/godam-mobile && npm run android:build:release" >&2
  exit 1
fi

mkdir -p "$DEST_DIR"
cp -f "$SRC" "$DEST"
echo "Copied to:"
ls -la "$DEST"
