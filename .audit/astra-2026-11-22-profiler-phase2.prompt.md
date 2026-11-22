Devin recomputed your p7/calibration medians from frames.csv (match) and committed everything as 6b023c9. The user chose to continue.

Decision on the overhead gate: the purpose is range attribution, not absolute FPS. Relax the profiler-overhead gate to <=5% mean and <=8% p95 of CPU-observed frame interval per scene, evaluated on BOTH off/on pairs (ABBA), and always report the measured overhead next to GPU ranges. State this change and its reason in the report. Do not change the other gates.

Continue, one GPU job at a time with the same pre-checks, fresh labels where a label already exists:
1. Finish the preview 7/8 ABBA with the profiler on: gp-p8-a, gp-p8-b, gp-p7-b, then gp-overhead-off-b (p7 off). (gp-p7-a and gp-overhead-off-a already exist and count as the first half.)
2. PHASE 2 rooms: 1.8.0 vs preview 3 in ABBA order on both-west and day-white (gp-stable-a, gp-p3-a, gp-p3-b, gp-stable-b), as in your plan, including the checks about the compiler pragma predicate, entity program fallback and separateEntityDraws when interpreting deltas. Note that 1.8.0/preview 3 lack some passes; report absent programs as absent.
3. Birch stages (birch-off, birch-torch) for 1.8.0 and preview 3 ONLY if you can validate the scene as your plan requires without more than modest work; otherwise skip and say so. Skip the optional program-binary probe.
4. Update reports/2026-11-22-gpu-profile/README.md and summary.json: per-range median/p95 tables for p7 vs p8, and 1.8.0 vs p3 (and p7 for context), paired deltas per range, which ranges explain the frame-time differences between packs, measured profiler overhead, and explicit limits (scene differences, what a range cannot separate, hypotheses still unproven).

Up to two diagnosed fix+retry cycles for runner/profiler bugs; stop on gate failures or any Lab/world change. No shader/dist/release/Lab changes, no commit/push/prune.

Final message: run statuses, overhead numbers, the p7 vs p8 table and the 1.8.0 vs p3 table (median ms per range, both scenes, paired deltas), your reading of where the preview-3 regression and the lamp cost sit, files changed, Lab check.
