#!/bin/bash
# Deterministic rebuild: generate -> package -> validate.  Usage: playable/build.sh <scratch-dir> <out.zip>
# (scratch-dir must not exist yet; out.zip must not exist yet; nothing in dist/ is overwritten.)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
scratch="$1"; out="$2"
python3 -I "$here/build_world.py" "$scratch"
python3 -I "$here/package.py" "$scratch/Aqualumen-Rain-Walk" "$out"
python3 -I "$here/validate_world.py" "$out" --json "$here/validation.json" --map "$here/map.txt" > "$here/validation.out"
sha256sum "$out"
