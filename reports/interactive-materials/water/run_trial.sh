#!/bin/bash
# Start only once copper and gold have handed the GPU slot to the water run.
set -u
cd "$(dirname "$0")" || exit 1
for variant in "${1:-candidate}" debug baseline; do
 for attempt in $(seq 1 48); do
  label="water-$variant-$attempt"
  if python3 capture.py "$variant" "$label" > "$variant-last.log" 2>&1; then break; fi
  if rg -q 'GPU busy' "$variant-last.log"; then sleep 10; continue; fi
  if [ -f "$label/preflight.json" ] && python3 -c 'import json,sys;exit(not bool(json.load(open(sys.argv[1])).get("foreignObservations")))' "$label/preflight.json"; then sleep 10; continue; fi
  cat "$variant-last.log"; exit 1
 done
 if [ ! -f "$label/complete.json" ]; then cat "$variant-last.log"; exit 1; fi
 python3 -c 'import json,sys;assert json.load(open(sys.argv[1]))["complete"]' "$label/complete.json" || exit 1
done
