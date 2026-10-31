#!/usr/bin/env bash
# Copy the built release APK into backend/uploads/, then push only that file to the VPS.
# Requires SSH: host godaam-vps in ~/.ssh/config (or set SSH_HOST) and write access to APP on the server.
#
# Usage (from repo root):
#   bash deploy/vps/push-apk-to-vps.sh
#   SSH_HOST=myvps APP=/opt/godaam bash deploy/vps/push-apk-to-vps.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SSH_HOST="${SSH_HOST:-godaam-vps}"
APP="${APP:-/opt/godaam}"

bash "$ROOT/scripts/copy-apk-to-backend-uploads.sh"

SRC="$ROOT/backend/uploads/mobile/GoDam.apk"
REMOTE="${SSH_HOST}:${APP}/backend/uploads/mobile/GoDam.apk"

echo "Uploading → $REMOTE"
ssh -o BatchMode=yes "$SSH_HOST" "mkdir -p '${APP}/backend/uploads/mobile'"
scp -o BatchMode=yes "$SRC" "$REMOTE"
echo "OK — restart API on the server if needed: sudo systemctl restart godaam-backend"
