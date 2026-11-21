# Independent prepared-water draw timing summary

Public read-only API: `audit(output_dir)`; CLI:

```sh
python3 -B tools/water_sun_prepared_timing.py OUTPUT_DIRECTORY
```

The input must be a completed `aqualumen-prepared-main-native-v1` packet with an executed timer and all declared main gates accepted. Missing/incomplete/modified evidence fails closed with exit 2. The tool never invokes GL, renders, installs, or edits the packet.

Four public CPU tests pass. Logs preserve three genuine software-only RED→GREEN verticals (missing CLI, state identity, input identity), followed by existing-policy negative checks for absent/pending input, ABBA/warmup order, fractional ns, sample counts, fixture order, hashes and duplicate JSON keys. All fixtures used by these tests are explicitly synthetic; no actual timer output existed during implementation.

The reader verifies exactly six fixture names/order, actual CSV/state chronology, ABBA cycle positions, warmup/measured sample counts, integer ns and hashes. It matches each draw to the physical program/source, queried guard before/after, counter bits, viewport/patch/five draw routes, source manifest files/attached-stage query hashes, input receipts and all eight actual raw-map payloads. Old/prepared inputs and matrix binary32 values must match per fixture. Source-query current program must only be restored, not equal the program whose attached source was queried, matching the producer's public seam.

Only measured draws contribute to per-fixture old/prepared medians in ms, min/max/population standard deviation/MAD, and paired ABBA cycle ratios. Each cycle ratio is mean(B draws)/mean(A draws), and the median ratio is median(prepared samples)/median(old samples). Ratios below 1 mean lower isolated native draw time; no statistical significance or general speedup conclusion is attached.

This is saved-telemetry consistency, not independent authentication, fresh GL execution, or a rerun of the main physics/node acceptance. Detailed sampler storage/filter/uniform-type proof remains the main saved-output auditor's responsibility. The output preserves Minecraft FPS, universal speedup, physical/visual/shipping acceptance as false. A synthetic result can never set `nativeTimerQualified`.

`HANDOFF.json` pins the source/test snapshots. Old sources, node/main harnesses, helper modules, packs and sealed packets were not changed.
