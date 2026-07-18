#!/usr/bin/env bash
# Build the launch-compatible Nuxt SSR output.
#
# This wrapper intentionally does not contact the backend: launch output must
# stay request-driven, with API calls handled at runtime by the SSR/Nginx path.

set -euo pipefail

echo "=== Building Nuxt launch output ==="
cd "$(dirname "$0")/../web-nuxt"
npm run build

echo "=== Done ==="
echo "Output: web-nuxt/.output/"
echo "Preview: node web-nuxt/.output/server/index.mjs"
