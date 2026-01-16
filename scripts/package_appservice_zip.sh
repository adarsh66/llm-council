#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO_ROOT"

echo "Building frontend…"
cd "$REPO_ROOT/frontend"
if command -v npm >/dev/null 2>&1; then
  npm ci
  npm run build
else
  echo "npm not found; install Node.js first" >&2
  exit 1
fi

echo "Copying frontend build into backend/static…"
rm -rf "$REPO_ROOT/backend/static"
mkdir -p "$REPO_ROOT/backend/static"
cp -R "$REPO_ROOT/frontend/dist/"* "$REPO_ROOT/backend/static/"

cd "$REPO_ROOT"

ZIP_NAME="appservice.zip"
rm -f "$ZIP_NAME"

echo "Creating $ZIP_NAME…"
zip -r "$ZIP_NAME" backend requirements.txt startup.sh >/dev/null

echo "Done: $REPO_ROOT/$ZIP_NAME"
