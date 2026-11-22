Devin reviewed .audit/astra-2026-11-22-profiler-plan.md. APPROVED in two phases. Implement PHASE 1 only now, then stop and report.

PHASE 1 (do now):
- The profiler mod (tools/gpu-profiler-mod/, tools/build-gpu-profiler.sh), runner integration (reports/2026-11-22-gpu-profile/run.py reusing the guarded animal-light runner and frame observer), parser/aggregation with CPU tests written red first, the calibration-pack generator, summarize.py.
- Ranges: whole frame; begin/prepare/shadowcomp/deferred/composite/final passes by program name; shadow capture (terrain + shadow entity flush as parents); Sodium terrain solid/cutout/translucent; main-pass entities. Entity/block-entity/hand fine-grained tagging is OPTIONAL in phase 1: if exact tagging proves fragile, publish a single entities parent range plus an explicit unclassified/residual instead of risky hooks. Never call Iris getPhase().
- Runs, in this order, each only after the previous exits and nvidia-smi/ps are idle: gp-cal-4x (calibration, on), gp-overhead-off-a (p7, off), gp-p7-a, gp-p8-a, gp-p8-b, gp-p7-b (on), gp-overhead-off-b (p7, off). Use the plan's gates (calibration 3x-5x with controls within max(0.10 ms,10%); overhead <=3% mean and <=5% p95 per scene and pair; reconciliation 0.02 ms). If calibration or overhead gates fail, stop and report instead of continuing to the pack comparison (one diagnosed retry with a fresh label is allowed).
- Write reports/2026-11-22-gpu-profile/README.md (Japanese, same report style) with per-range median/p95 for both scenes and both packs, the calibration and overhead results, and explicit limits. Clearly separate GPU timer-query ranges from CPU-observed frame intervals and from glcheck harness timings.

PHASE 2 (do NOT start): 1.8.0 vs preview 3 rooms, birch stages, optional program-binary probe.

Constraints: no shader source changes to release/ or dist/ packs (the calibration ZIP is an ignored diagnostic under build/); no Lab installation; no git commit/push/prune; stop on any unrecognized jar or missing/duplicate injection. If the hook verification against the pinned jars shows a planned site does not exist, adapt minimally and explain.

Final message: files created/changed, test red->green summary, build output (jar SHA-256), injection verification summary, every run's status, gate results with numbers, the per-range table for both scenes (p7 vs p8 medians and p95), uncovered/residual share, and Lab check.
