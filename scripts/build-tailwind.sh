#!/usr/bin/env bash
# Build the site's Tailwind CSS (replaces the runtime Play CDN).
# Usage: scripts/build-tailwind.sh [version]
set -euo pipefail

VERSION="${1:-3.4.17}"
BIN="node_modules/.bin/tailwindcss"

if ! command -v tailwindcss >/dev/null 2>&1 && [ ! -x "$BIN" ]; then
    echo "No tailwindcss found; downloading standalone CLI v${VERSION}..."
    mkdir -p node_modules/.bin
    OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
    ARCH="$(uname -m)"
    [ "$ARCH" = "x86_64" ] && ARCH="x64"
    [ "$ARCH" = "aarch64" ] && ARCH="arm64"
    curl -sSL "https://github.com/tailwindlabs/tailwindcss/releases/download/v${VERSION}/tailwindcss-${OS}-${ARCH}" -o "$BIN"
    chmod +x "$BIN"
fi

CMD="tailwindcss"
[ -x "$BIN" ] && CMD="$BIN"

"$CMD" -c tailwind.config.js -i assets/css/tailwind.input.css -o static/css/tailwind.build.css --minify
echo "Built static/css/tailwind.build.css"
