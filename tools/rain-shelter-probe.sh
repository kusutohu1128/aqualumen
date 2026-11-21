#!/usr/bin/env bash
# Build the native fixture, or run it with an optional output path.
set -euo pipefail
cd "$(dirname "$0")/.."
make build/rain-shelter-probe
if [[ ${1:-} == run ]]; then
    build/rain-shelter-probe release/shaders "${2:-build/rain-shelter-latest.json}"
fi
