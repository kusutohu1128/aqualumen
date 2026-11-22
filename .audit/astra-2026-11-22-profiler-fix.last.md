**Calibration passed at 4.010×. Phase 1 stopped at the noon overhead gate.** With the profiler enabled, p7’s mean CPU-observed frame interval increased **3.335%** against a 3% limit, and p95 increased **5.107%** against a 5% limit. Preview 8 was never launched. [Japanese report](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/README.md) · [Machine-readable results](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/summary.json)

The p7 measurements localize the largest cost in the two-lamp night scene to **solid terrain drawing**, at **8.713 ms median**, followed by **shadowcomp**, at **4.343 ms**. At noon those ranges fell to **2.400 ms** and **0.554 ms**, while **prepare** rose to **3.344 ms**. The scenes differ in roof, time, and lighting, so these measurements cannot isolate the cost of one lamp or establish register pressure as the cause.

### Gates

| CPU-observed frame interval | Night, off → on | Increase | Noon, off → on | Increase |
|---|---:|---:|---:|---:|
| Mean | 25.509 → 25.812 ms | +1.190% | 14.655 → 15.144 ms | **+3.335%** |
| p95 | 27.305 → 27.835 ms | +1.941% | 16.115 → 16.938 ms | **+5.107%** |

Four calibrated shadow dispatches took **6.7379 ms** against **1.6804 ms** for the single p7 dispatch. The `prepare2` and `final` control medians each differed by **0.001024 ms**, within their **0.100 ms** limits. The ceiling image differed by **0.000 display codes** in mean RGB. All **2,033 accepted GPU frames** reconciled with **0.000 ms** maximum error, against a 0.020 ms limit. There were zero query drops or hook exceptions in the resumed measurements.

### Run status

| Run | Outcome | Accepted frames, night / noon |
|---|---|---:|
| `gp-cal-4x` | Earlier recursive loading-screen failure | 0 / 0 |
| `gp-cal-4x-retry` | Earlier empty shadow-slot failure | 0 / 0 |
| `gp-cal-4x-c` | Completed and passed calibration | 327 / 657 |
| `gp-overhead-off-a` | Completed with the CPU observer alone | 393 / 683 |
| `gp-p7-a` | Completed and triggered the noon overhead stop | 388 / 661 |
| `gp-p8-a`, `gp-p8-b`, `gp-p7-b`, `gp-overhead-off-b` | Unstarted under the gate rule | — |

The retained cache contained an 11,309,257-byte data file and its 11,816-byte index. The resumed calibration reached the Overworld worker-start marker in **20 seconds**, compared with **297 seconds** on the earlier retry. Launch to the first post-worker observer batch was **20.5 s**, **21.4 s**, and **20.5 s** for the three completed clients.

### GPU ranges

Values are in-game timer-query **median / p95 in milliseconds**. Both p8 columns are unmeasured for every range. Parent ranges include their children. The CPU intervals above were measured separately, and no glcheck harness timings enter these tables.

| Range | p7 night | p7 noon |
|---|---:|---:|
| Whole frame | 21.830 / 23.239 | 12.015 / 12.924 |
| Solid terrain | 8.713 / 9.144 | 2.400 / 2.707 |
| Cutout terrain | 0.043 / 0.044 | 0.043 / 0.044 |
| Translucent terrain | 0.029 / 0.030 | 0.029 / 0.030 |
| Main entities | 1.527 / 1.792 | 0.645 / 0.674 |
| Shadow capture | 0.767 / 1.104 | 0.599 / 0.824 |
| Shadow terrain | 0.584 / 0.927 | 0.420 / 0.644 |
| Shadow solid | 0.056 / 0.057 | 0.052 / 0.054 |
| Shadow cutout | 0.492 / 0.836 | 0.332 / 0.556 |
| Shadow translucent | 0.031 / 0.032 | 0.031 / 0.032 |
| Shadow entity flush | 0.103 / 0.105 | 0.105 / 0.106 |
| Shadow batched entities | 0.102 / 0.103 | 0.104 / 0.104 |
| Begin stage | 0.033 / 0.035 | 0.033 / 0.034 |
| Prepare stage | 1.787 / 2.087 | 3.344 / 3.829 |
| Shadowcomp stage | 4.343 / 4.781 | 0.554 / 0.556 |
| Deferred stage | 0.644 / 0.660 | 0.654 / 0.892 |
| Composite stage | 2.178 / 2.426 | 2.063 / 2.306 |
| Final stage | 0.189 / 0.190 | 0.190 / 0.190 |
| Barriers | 0.016 / 0.019 | 0.016 / 0.019 |
| **Uncovered** | **1.413 / 1.917** | **1.264 / 1.680** |

**Uncovered share of total GPU time was 6.64% at night and 10.81% at noon.** The following are the individual draw and dispatch ranges. The report also gives each enclosing pass’s median and p95. [Full per-range tables](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/README.md)

| Program | p7 night | p7 noon |
|---|---:|---:|
| `begin` dispatch | 0.012 / 0.012 | 0.012 / 0.012 |
| `begin1` dispatch | 0.011 / 0.012 | 0.011 / 0.012 |
| `prepare` quad | 1.234 / 1.355 | 1.605 / 1.751 |
| `prepare1` quad | 0.239 / 0.292 | 0.247 / 0.299 |
| `prepare2` dispatch | 0.213 / 0.221 | 0.214 / 0.222 |
| `prepare3` dispatch | 0.031 / 0.032 | 0.049 / 0.050 |
| `prepare4` dispatch | 0.040 / 0.040 | 1.184 / 1.418 |
| `shadowcomp` dispatch | 0.005 / 0.006 | 0.005 / 0.006 |
| `shadowcomp1` dispatch | 0.077 / 0.078 | 0.068 / 0.069 |
| `shadowcomp2` dispatch | 0.932 / 1.159 | 0.394 / 0.395 |
| `shadowcomp3` dispatch | 1.625 / 1.833 | 0.036 / 0.037 |
| `shadowcomp4` dispatch | 1.680 / 1.931 | 0.029 / 0.030 |
| `deferred` quad | 0.638 / 0.641 | 0.648 / 0.679 |
| `composite` quad | 2.058 / 2.073 | 1.953 / 1.959 |
| `composite1` quad | 0.070 / 0.073 | 0.070 / 0.072 |
| `composite2` quad | 0.016 / 0.017 | 0.016 / 0.017 |
| `composite3` dispatch | 0.010 / 0.011 | 0.008 / 0.008 |
| `final` quad | 0.183 / 0.184 | 0.184 / 0.184 |

### Build, tests, and files

The profiler JAR SHA-256 is `75d6e7307d9437c3aa165d25530878ea7f42456644e7112713728cc2c918ea20`. Both profiled clients matched all **8 target classes and 51 verified instruction sites** on `NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2`, OpenGL `3.2.0 NVIDIA 580.173.02`, with 64-bit timestamps.

The new Java test reproduced the original `NoSuchElementException`, then passed for empty, unmapped, and mapped slots. Every accepted frame recorded empty slots **8–99** in calibration and **5–99** in p7. An injected hook exception was counted once and disabled subsequent callbacks. All **8 profiler Python tests** and **4 existing frame-extraction tests** passed. I independently recomputed every reported GPU median and p95 from the accepted CSVs.

Files created or changed in this continuation:

- `tools/gpu-profiler-mod/` — `Timers.java`, `Hooks.java`, new `SafeHooks.java`, and new `AttributionTest.java`, plus the [build script](/home/kusutohu/repos/aqualumen/tools/build-gpu-profiler.sh).
- `reports/2026-11-22-gpu-profile/` — `run.py`, `profile_data.py`, `test_profile.py`, `summarize.py`, `README.md`, and `summary.json`.
- `runs/` — updated `progress.txt` and `result.json`; added logs, preflights, observer and scene receipts, captures, accepted CSVs, and summaries for the [calibration](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/runs/gp-cal-4x-c/summary.json), [p7 off](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/runs/gp-overhead-off-a/summary.json), and [p7 on](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/runs/gp-p7-a/summary.json) runs. Ignored build outputs hold the JARs, raw streams, cache, and gate log.

**Lab verification passed.** All eight protected hashes, the Lab metadata digest, and the source-world contents matched before and after each run. Lab still selects 1.8.0 with physics 0.2.0 active and lighting compiler 0.3.0 disabled. The final GPU/process check found zero competing jobs. No dist or release files changed. No commit, push, or prune was performed.