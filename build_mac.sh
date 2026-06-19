#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
APP_NAME="Tidal Playlist Creator"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This build script must run on macOS."
  exit 1
fi

build_app() {
  "$PYTHON_BIN" -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --name "$APP_NAME" \
    --osx-bundle-identifier "com.local.tidalplaylistcreator" \
    --collect-all tidalapi \
    "$@" \
    main.py
}

if [[ -f "resources/icons/app.icns" ]]; then
  build_app --icon "resources/icons/app.icns"
else
  build_app
fi

echo "Built: dist/$APP_NAME.app"
