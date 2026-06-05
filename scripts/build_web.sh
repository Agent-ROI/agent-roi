#!/usr/bin/env bash
# Build the React web UI and copy it into the Python package so that a
# pip/uv install of agent-roi can serve the dashboard via `agent-roi serve`.
#
# Run this before building a wheel/sdist:
#   ./scripts/build_web.sh && uv build
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB="$ROOT/web"
DEST="$ROOT/src/agent_roi/webui"

echo "==> Building web UI"
cd "$WEB"
npm ci
npm run build

echo "==> Copying build into package: $DEST"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -R "$WEB/dist/." "$DEST/"

echo "==> Done. Packaged web UI at src/agent_roi/webui"
