**Preview 3 reproduced the slowdown in the lava-free birch scene.** With the torch off, p3 added **5.036 ms per mean GPU frame** over 1.8.0. The fullscreen deferred and composite stages accounted for **2.823 ms, or 56%**, followed by visible terrain at **1.797 ms**. The CPU-observed frame interval increased **5.249 ms**. Both run orders showed the regression. The timings locate the cost, but register pressure and occupancy remain unmeasured.

**One torch increased both terrain shading and shadow-compute time.** At the same birch camera, the mean GPU frame increased **11.551 ms on 1.8.0** and **9.787 ms on p3**.

| Mean GPU contribution, torch minus off | 1.8.0 | p3 |
|---|---:|---:|
| Cutout terrain | +4.006 ms | +3.991 ms |
| Solid terrain | +2.314 ms | +2.278 ms |
| Shadow-compute stage | +5.173 ms | +3.566 ms |
| **Whole GPU frame** | **+11.551 ms** | **+9.787 ms** |
| **CPU-observed frame interval** | **+11.781 ms** | **+9.926 ms** |

Preview 8 had a smaller effect. Its final fullscreen draw added **0.01536 ms in both scenes and both orders**. Its exposure compute dispatch changed by 0.000 ms at night and −0.001 ms at noon. The paired whole-frame median differences were +0.204 and +0.143 ms, with appreciable variation between orders. [Japanese report](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/README.md) · [Machine-readable results](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/summary.json)

### Profiler overhead and gates

Both p7 off/on pairs passed the revised **5% mean / 8% p95** limits. These are increases in the **CPU-observed frame interval**. The report records the former 3% / 5% limits and the decision to accept the measured perturbation for range attribution. Direct overhead controls cover the p7 rooms.

| Pair | Scene | Mean increase | p95 increase |
|---|---|---:|---:|
| A, off → on | Night, two lamps | +1.190% | +1.941% |
| A, off → on | Noon | +3.335% | +5.107% |
| B, on → off | Night, two lamps | +1.827% | +1.690% |
| B, on → off | Noon | +4.054% | +1.149% |

Calibration passed at **4.010×**. Both control ranges differed by **0.001024 ms**, and the reference image region differed by **0 display codes**. Across **13,024 accepted GPU frames**, maximum reconciliation error was **0.000 ms** against the 0.02 ms limit. No accepted window lost a frame.

### Preview 7 vs preview 8

Each cell gives **older median / newer median / paired Δ**, in GPU milliseconds. Pack medians pool the two runs. Δ averages the two within-pair median differences, giving each run order equal weight. The tables below show the whole frame and its direct ranges. Every nested shadow range, named program, dispatch, quad, barrier and outer pass has a median, p95 and paired delta in the linked tables. [Full p7/p8 range tables](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/README.md:101)

| GPU range | Night, two lamps | Noon |
|---|---:|---:|
| **Whole frame** | **22.177 / 22.295 / +0.204** | **12.232 / 12.337 / +0.143** |
| Terrain solid | 8.795 / 8.818 / +0.040 | 2.402 / 2.402 / 0.000 |
| Terrain cutout | 0.043 / 0.043 / 0.000 | 0.043 / 0.042 / −0.001 |
| Terrain translucent | 0.029 / 0.029 / 0.000 | 0.029 / 0.029 / 0.000 |
| Main entities | 1.554 / 1.584 / −0.014 | 0.645 / 0.646 / +0.001 |
| Shadow capture | 0.767 / 0.780 / +0.011 | 0.624 / 0.633 / +0.008 |
| Begin | 0.033 / 0.033 / 0.000 | 0.033 / 0.033 / 0.000 |
| Prepare | 1.797 / 1.811 / +0.014 | 3.376 / 3.408 / +0.009 |
| Shadowcomp | 4.353 / 4.358 / −0.002 | 0.553 / 0.553 / −0.001 |
| Deferred | 0.645 / 0.645 / +0.001 | 0.654 / 0.655 / 0.000 |
| Composite | 2.180 / 2.183 / +0.003 | 2.065 / 2.066 / +0.002 |
| Final | 0.189 / 0.205 / +0.015 | 0.190 / 0.206 / +0.015 |
| Uncovered | 1.427 / 1.432 / +0.007 | 1.323 / 1.327 / +0.010 |

### 1.8.0 vs preview 3

| GPU range | Night, two lamps | Noon |
|---|---:|---:|
| **Whole frame** | **18.536 / 18.906 / +0.521** | **7.681 / 9.777 / +2.117** |
| Terrain solid | 8.098 / 8.172 / +0.086 | 1.911 / 2.135 / +0.226 |
| Terrain cutout | 0.086 / 0.091 / +0.005 | 0.044 / 0.044 / +0.001 |
| Terrain translucent | 0.091 / 0.114 / +0.023 | 0.033 / 0.032 / −0.001 |
| Main entities | 0.618 / 1.245 / +0.627 | 0.127 / 0.325 / +0.197 |
| Shadow capture | 0.773 / 0.778 / +0.006 | 0.600 / 0.606 / +0.004 |
| Begin | 0.033 / 0.033 / 0.000 | 0.033 / 0.034 / 0.000 |
| Prepare | 1.508 / 1.503 / −0.006 | 2.087 / 1.886 / −0.198 |
| Shadowcomp | 4.290 / 2.494 / −1.797 | 0.136 / 0.520 / +0.385 |
| Deferred | 0.260 / 0.652 / +0.391 | 0.260 / 0.648 / +0.388 |
| Composite | 0.767 / 2.179 / +1.413 | 0.731 / 2.033 / +1.302 |
| Final | 0.190 / 0.189 / −0.001 | 0.190 / 0.190 / −0.001 |
| Uncovered | 1.396 / 1.364 / −0.030 | 1.235 / 1.252 / +0.014 |

At night, p3’s faster `shadowcomp3` dispatch offset much of the increase in fullscreen and entity work. At noon, composite was the largest increase. Both older packs use the `TexturedLit` entity fallback. Enabling `separateEntityDraws` in p3 coincided with **2 → 5 main entity flushes**, with **one actual draw per frame** in both packs. The compiler pragma applied on p3 through both logged paths. Its source predicate did not match 1.8.0. `prepare2/3/4` and `shadowcomp4` are absent from both older ZIPs. [Full 1.8.0/p3 range tables with p7 context](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/README.md:223)

The older-pack rooms had a wider field of view than the p7/p8 rooms. Each ABBA comparison matched projection internally. The p7 reference column therefore provides cross-generation context only. Night and noon also differ in roof and time of day, which is why the single-lamp result comes from the fixed birch camera. Uncovered GPU time ranged from **6.59–16.43%** in the rooms and **4.11–6.58%** at the birch. [Birch range tables](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/README.md:345)

### Runs, files and Lab

| Runs | Status |
|---|---|
| `gp-cal-4x-c`, `gp-overhead-off-a`, `gp-p7-a` | Prior accepted receipts reused |
| `gp-p8-a`, `gp-p8-b`, `gp-p7-b`, `gp-overhead-off-b` | Completed and validated |
| `gp-stable-a` | Client completed. Excluded because birch landmark checks detected a field-of-view mismatch |
| `gp-stable-a-retry1`, `gp-p3-a`, `gp-p3-b`, `gp-stable-b` | Completed and validated in order, with both rooms and both birch stages |

One diagnosed retry restored the historical spectator projection. The accepted birch captures reached a minimum landmark correlation of **0.967** against the **0.75** threshold. The checked 262,144-block volume contained zero lava blocks. All 14 CPU tests passed, and an independent CSV calculation reproduced the per-range medians, p95s and paired deltas.

Changed files were `README.md`, `summary.json`, `run.py`, `summarize.py`, `profile_data.py`, `test_profile.py`, `runs/progress.txt` and `runs/result.json` under the GPU-profile report, plus the shared timing extractor. Added `birch_scene.py`, `comparisons.py` and the nine new run directories with their logs, receipts and measurements. [Report directory](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile) · [Timing extractor](/home/kusutohu/repos/aqualumen/reports/2026-11-21-animal-light/timing/measure.py)

**Lab verification passed.** All eight protected file hashes, the Lab tree metadata digest, and the original world and configuration matched before and after. Lab still selects **1.8.0**, with physics **0.2.0 active** and compiler **0.3.0 disabled**. HEAD remains `6b023c9`. [Final preflight receipt](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/runs/gp-stable-b/preflight.json)