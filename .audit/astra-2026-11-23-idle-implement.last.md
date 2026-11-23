**Candidate 9 preserved the tested images but failed the performance gate.** At birch-off, deferred and composite together saved **0.089 ms and 0.111 ms** in the two measurement orders. The requirement was **2.0 ms in each order**. The whole GPU frame took **0.119 ms and 0.059 ms longer**. I stopped at that gate before the two-program split or the CPU-observer-only candidate comparison.

### What caused the fullscreen cost

Four single-factor diagnostic packs were measured in 16 Minecraft launches at birch-off. Values are mean GPU milliseconds saved in the two independent pairs.

| Diagnostic change on preview 3 | Pair A | Pair B |
|---|---:|---:|
| Use lamp-only lighting in composite, keeping the NVIDIA pragma | 1.159 | 1.160 |
| Remove the pragma from that lamp-only composite | 0.199 | 0.199 |
| Remove deferred’s pending-receiver lighting and its dependent inputs, keeping all five outputs and the pragma | 1.416 | 1.408 |
| Remove the fifth output and its C14 read from that lean deferred program | 0.011 | 0.038 |

The cost followed the lighting code compiled into the two fullscreen programs. The fifth render target explained little of deferred’s increase. The fast diagnostics could not ship as written: with one captured lava cell, they lost measurable underwater scattering and opaque-surface lighting. The timings do not establish register pressure or occupancy as the mechanism. [Submitted shader diffs and diagnostic results](/home/kusutohu/repos/aqualumen/reports/2026-11-23-lava-idle/README.md)

### Preview 8 vs candidate 9

Each cell gives **p8 → p9 pooled median GPU ms**, followed by the **paired mean deltas A / B** in parentheses. Negative deltas are faster.

| Scene | Deferred | Composite | Shadowcomp2 dispatch | Whole GPU frame |
|---|---|---|---|---|
| Both-west, two lamps | 0.648 → 0.609 (−0.041 / −0.039) | 2.065 → 2.026 (−0.044 / −0.040) | 0.933 → 0.934 (−0.010 / +0.002) | 21.926 → 21.788 (−0.182 / −0.110) |
| Day-white, noon | 0.644 → 0.616 (−0.028 / −0.026) | 1.920 → 1.882 (−0.039 / −0.038) | 0.394 → 0.394 (+0.000 / −0.001) | 11.989 → 11.965 (−0.053 / +0.019) |
| Birch-off | 1.827 → 1.753 (−0.068 / −0.076) | 1.996 → 1.964 (−0.021 / −0.035) | 0.417 → 0.417 (+0.002 / +0.000) | 29.601 → 29.628 (+0.119 / +0.059) |
| Birch-torch | 1.832 → 1.753 (−0.080 / −0.076) | 2.001 → 1.964 (−0.037 / −0.037) | 0.963 → 0.963 (+0.009 / −0.001) | 43.811 → 43.945 (+0.440 / −0.124) |

All four profiler runs and both overhead controls completed. Across 6,197 accepted frames, maximum reconciliation error was **0.000 ms**. Profiler overhead stayed within the limits in every scene and order, peaking at **4.10% mean** and **3.23% p95**. The full table contains all 55 ranges per scene, including p95 and both paired deltas. [Full per-range CSV](/home/kusutohu/repos/aqualumen/reports/2026-11-23-lava-idle/range-times.csv)

**Minecraft frame intervals.** The two profiler-off p8 controls averaged **33.160 / 33.328 ms** at birch-off. During the profiler-on ABBA, the CPU observer measured p9 taking **0.255 / 0.144 ms longer** there. The failed GPU gate stopped the separate CPU-observer-only ABBA, so there is no profiler-off p9 FPS result. [Frame intervals for all four scenes](/home/kusutohu/repos/aqualumen/reports/2026-11-23-lava-idle/README.md#Minecraft-のフレーム間隔と停止判断)

### Candidate, proof, and workspace

- The candidate changes `composite.fsh`, `deferred.vsh`, `deferred.fsh`, and `lib/idle_deferred.glsl` in the topmost overlay. Composite returns early in air. Deferred selects a lean path when the entire captured lava grid is empty. Both paths still share one linked program. I left the shadowcomp2 cache intact. Its historical **+0.392 ms** was measured for the whole dispatch, and the store’s individual cost remains unresolved. [Overlay](/home/kusutohu/repos/aqualumen/release/idle-preview/shaders/) · [Build change](/home/kusutohu/repos/aqualumen/tools/build.py)
- Preview 8 failed the new empty-route test as intended. Candidate 9 passed it and matched p8 **bit-for-bit in all 25 replay conditions** on the RTX 3080 Ti and Mesa llvmpipe, including lava-present scenes, final display output, and exposure history. I corrected an undersized C14 test fixture and repeated the proof. All seven existing checks and all seven candidate regression checks passed. The CPU suites passed 3 new and 10 existing tests. [NVIDIA proof](/home/kusutohu/repos/aqualumen/reports/2026-11-23-lava-idle/candidate-full-nvidia.log) · [Mesa proof](/home/kusutohu/repos/aqualumen/reports/2026-11-23-lava-idle/candidate-full-mesa.log)
- Supporting changes cover the [Makefile](/home/kusutohu/repos/aqualumen/Makefile), [glcheck](/home/kusutohu/repos/aqualumen/tools/glcheck.cpp), [replay probe](/home/kusutohu/repos/aqualumen/tools/lava-idle-probe.h), [guarded runner](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/run.py), and [campaign scripts and receipts](/home/kusutohu/repos/aqualumen/reports/2026-11-23-lava-idle/). One untimed source capture was rejected for an incorrect offhand-marker check and passed under a fresh label after correction.
- Stable and previews 3–8 rebuilt byte-identically. All **133 dist hashes** and all **eight Lab hashes** matched their baselines, as did Lab tree metadata and original world/config checks. Lab still selects 1.8.0 with physics 0.2.0 active and compiler 0.3.0 disabled. The unpublished candidate is under `build/lava-idle` with SHA-256 `4184d8cdf12634f108e3379d5b600de5009349916dfea26f7ad59f9190748f0f`. HEAD remains `64f4379`. [Machine-readable results](/home/kusutohu/repos/aqualumen/reports/2026-11-23-lava-idle/summary.json)