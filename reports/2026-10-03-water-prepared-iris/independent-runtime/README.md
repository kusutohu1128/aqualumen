# CPU runtime wrapper, frozen v1

Eight public synthetic saved-file tests and twelve unchanged support-runtime tests passed. These are CPU contract checks, not Iris/shader evidence. Initial missing-interface RED and the subsequent physical-role classification RED are preserved separately; neither is a rendering failure.

Replay:

```sh
python3 -B -m unittest discover -s tools -p test_water_sun_prepared_runtime.py
python3 -B -m unittest discover -s tools -p test_water_sun_support_runtime.py
python3 -B tools/water_sun_prepared_runtime.py RAW.json NEW-PREPARED.zip GUARD.json
```

The wrapper verifies the complete prepared pack through public exact parent recovery, then validates that recovered original zero-support parent. It reads the original saved RAW and guard against the NEW filename and digest; it does not manufacture old identities, filter samples or mutate raw files to fit an old qualifier. The shared binding/state and per-point numerical gates remain unchanged. Original artifacts/validators were not edited.

Reasons keep all sixteen points and the minimum four qualified-applied threshold. Valid evidence with fewer than four emits a negative JSON report and exits 1. The packed same-draw counts remain zero/support/unknown/calls; zero plus rejection double-counts and unknown without original other-group rejection fail. Per-node categories beyond the first reason are not inferred from grouped counts.

Inputs keep the raw first target, view, mean and covariance and invoke the frozen independent references. C12 is not TES in this role; a zero code means no observed first failure, not application or a continuous zero. Physical display intentionally has no selected FINAL readback contract and is rejected explicitly after exact recovery, rather than being relabeled as the old observer pack.

Guard and FINAL snapshots are separate frames from each other and from PNG captures. The wrapper does not qualify all48 raw arithmetic, actual drawing/fragment fetching, passivity, physics/energy/reciprocity, appearance/motion, FPS floors or shipping. No actual capture was run or audited for this CPU handoff. `HANDOFF.json` records exact source/test/dependency/pack pins; current code and its matching snapshots are stable.
