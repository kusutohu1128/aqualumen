#!/usr/bin/env bash
# Reproduce the weather-light staging candidate and its evidence. Writes only build/weather-light-staging/ and this directory.
# GPU work is sub-second (shader compile + 1-pixel draws), so no render lock is taken; do not run it while a 1440p benchmark
# is between its ready marker and completion (reports/2026-11-21-rain-eaves/material/take-N/client.log).
# Usage: reports/2026-11-21-rain-eaves/weather-light/reproduce.sh [--no-mutants]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; repo="$(cd "$here/../../.." && pwd)"; st="$repo/build/weather-light-staging"
cd "$repo"
python3 -I "$here/make_staging.py"
g++ -std=c++17 -O1 -w -I tools "$here/weather_light_probe.cpp" -o "$st/weather_light_probe" -lepoxy -lEGL
"$st/weather_light_probe" --glcheck "$st/pack/shaders" --compile-only > "$here/compile-only.log" 2>&1
"$st/weather_light_probe" "$st/pack/shaders" "$st/baseline-rc3/shaders" "$here/evidence.json" | tee "$here/probe.log"
python3 -I "$here/verify_package.py"
if [ "${1:-}" != "--no-mutants" ]; then python3 -I "$here/mutation_check.py"; fi
python3 -I "$here/finalize.py"
