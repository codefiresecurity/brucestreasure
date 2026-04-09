#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT_DIR/build/browser_app"
WEB_DIR="$APP_DIR/build/web"
DOCS_DIR="$ROOT_DIR/docs"
TEMPLATE="$ROOT_DIR/pygbag-local.tmpl"
PYGBAG_RUNTIME_VERSION="0.9.2"
PYGBAG_RUNTIME_CDN="https://pygame-web.github.io/archives/0.9/"
PYGBAG_PYBUILD="3.12"
LOCAL_ICON="$ROOT_DIR/assets/tnt.png"

"$ROOT_DIR/prepare_browser_build.sh"
rm -rf "$APP_DIR/build"

python -m pygbag \
  --build \
  --disable-sound-format-error \
  --version "$PYGBAG_RUNTIME_VERSION" \
  --PYBUILD "$PYGBAG_PYBUILD" \
  --cdn "$PYGBAG_RUNTIME_CDN" \
  --icon "$LOCAL_ICON" \
  --template "$TEMPLATE" \
  "$APP_DIR"

mkdir -p "$DOCS_DIR"
cp "$WEB_DIR/index.html" "$DOCS_DIR/index.html"
cp "$WEB_DIR/browser_app.apk" "$DOCS_DIR/browser_app.apk"
cp "$WEB_DIR/browser_app.tar.gz" "$DOCS_DIR/browser_app.tar.gz"
cp "$WEB_DIR/favicon.png" "$DOCS_DIR/favicon.png"
cp "$WEB_DIR/favicon.png" "$DOCS_DIR/favicon.ico"

cat > "$DOCS_DIR/browser_app.html" <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=/">
  <title>Redirecting</title>
</head>
<body>
  <p>Redirecting to <a href="/">/</a>...</p>
</body>
</html>
EOF

echo "Built browser site:"
echo "  $DOCS_DIR/index.html"
echo "  $DOCS_DIR/browser_app.apk"
echo
echo "Test locally with:"
echo "  python -m http.server -d $DOCS_DIR 8000"
