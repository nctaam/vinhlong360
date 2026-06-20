#!/bin/bash
# Build Nuxt with prerendered static pages.
# Requires backend running at localhost:8360.
#
# Usage:
#   # Start backend first (in another terminal):
#   BUILD_SEARCH_INDEXES=false BACKGROUND_INDEX_BUILD=false SCHEDULER_ENABLED=false python agent/server.py
#
#   # Then run this script:
#   bash scripts/build-prerender.sh

set -e

echo "=== Checking backend is running ==="
if ! curl -sf http://localhost:8360/health > /dev/null 2>&1; then
  echo "ERROR: Backend not running at localhost:8360"
  echo "Start it first: python agent/server.py"
  exit 1
fi

echo "=== Building Nuxt with prerender ==="
cd web-nuxt
npm run build

echo "=== Done ==="
echo "Output: web-nuxt/.output/"
echo "Preview: node web-nuxt/.output/server/index.mjs"
