Devin reviewed .audit/astra-2026-11-23-idle-plan.md: APPROVED with scope limits to keep this practical.

- Order of work: (a) attribution diagnostics, (b) smallest fix that the diagnostics justify, (c) proof, (d) profiler ABBA p8 vs candidate 9, (e) CPU-observer-only ABBA for Minecraft frame intervals. Report after (e). Do not publish to dist/ or Lab.
- Diagnostics budget: at most 4 single-factor diagnostic packs (prioritise composite source-vs-pragma and deferred source-vs-fifth-MRT; shadowcomp2 store only if cheap), each one control/diag pair in ABBA at birch-off only. If a simple compile-time separation (composite not pulling area-light code it cannot use; deferred lean path) explains the cost, stop diagnosing and build that.
- Fix preference: single-program compile-time specialisation first. Use the two-program/clip + explicit-flip design ONLY if the single-program route cannot recover >=2.0 ms combined at birch-off; if you need it, pause and report before implementing it (it changes pass slots and is riskier).
- Shadowcomp2 cache skip: include only if cache semantics are provably preserved; otherwise leave it and report its cost.
- Topmost overlay release/idle-preview + `--idle-preview` in tools/build.py is accepted (flattening deferred). Rebuild check: stable and previews 3-8 must still reproduce their published ZIP hashes.
- Image proof: bitwise equality p8 vs candidate on NVIDIA for the listed lava-free and lava-present scenes; Mesa run at least for the new probe. Existing make targets stay green.
- Measurement gates and stop conditions as in your plan (>=2.0 ms combined at birch-off in both pairs, net whole-frame saving, no reproducible regression elsewhere).
- Up to two diagnosed fix+retry cycles for tooling bugs. No commit/push/prune; no Lab/dist changes.

Final message: what caused each increase (with diagnostic numbers), the fix actually built (files), proof results, the p8 vs p9 per-range table for all four scenes with paired deltas, Minecraft frame-interval ABBA, anything skipped, Lab/dist check.
