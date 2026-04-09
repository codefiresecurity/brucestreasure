#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$ROOT_DIR/build/browser_app"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

cp "$ROOT_DIR/browser_main.py" "$BUILD_DIR/main.py"
cp "$ROOT_DIR/bruce_game.py" "$BUILD_DIR/bruce_game.py"
cp "$ROOT_DIR/narratives.json" "$BUILD_DIR/narratives.json"
cp "$ROOT_DIR/highscores.txt" "$BUILD_DIR/highscores.txt"
cp -R "$ROOT_DIR/assets" "$BUILD_DIR/assets"

echo "Prepared browser app in: $BUILD_DIR"
echo "Next step: ./build_pages.sh"
