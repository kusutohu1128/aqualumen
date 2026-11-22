**Phase 1 stopped at calibration after the permitted retry.** The profiler built, but neither attempt produced a benchmark-scene frame. There is no measured p7–p8 performance difference or pass-cost ranking from this campaign. [Japanese report](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/README.md) · [Machine-readable results](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/summary.json)

| Run | Status |
|---|---|
| `gp-cal-4x` | Stopped during world entry after 19.2 s. Minecraft recursively rendered a loading screen while a frame query was open. |
| `gp-cal-4x-retry` | With recursive frames excluded, reached Overworld rendering. The profiler threw `NoSuchElementException` when it tried to name an empty Iris shadow-composite slot. The client exited after 300.5 s. |
| `gp-overhead-off-a`, `gp-p7-a`, `gp-p8-a`, `gp-p8-b`, `gp-p7-b`, `gp-overhead-off-b` | All six remained unstarted under the calibration stop rule. |

**Build and injection verification.** The retry used profiler JAR SHA-256 `0c334d1638f6e487ae26a330a20cf5e6e6dbe85c745e2f3c2f3446f460be54da`. All **8 target classes** loaded once with the same **51 counted bytecode sites** as the offline verifier. The runtime reported `NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2`, OpenGL `3.2.0 NVIDIA 580.173.02`, and 64-bit timestamps. The GL binding check passed. The failure occurred in pass attribution after injection. [Retry log](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/runs/gp-cal-4x-retry/client.log)

**Timing and gates.** The two attempts recorded 85 and 3 loading-only whole frames. **Zero frames** entered an accepted scene window. The 3–5× calibration ratio, control-pass tolerance of max(0.10 ms, 10%), one-code image tolerance, 3% mean / 5% p95 CPU frame-interval overhead limits, and 0.02 ms reconciliation limit are all **unevaluated**. No glcheck timing was used.

| GPU range, median / p95 in ms | both-west p7 | both-west p8 | day-white p7 | day-white p8 |
|---|---:|---:|---:|---:|
| Whole frame | — | — | — | — |
| Each begin, prepare, shadowcomp, deferred, composite and final program | — | — | — | — |
| Shadow capture, terrain and entity flush | — | — | — | — |
| Sodium solid, cutout and translucent terrain | — | — | — | — |
| Main entities | — | — | — | — |
| Uncovered time and residual share | — | — | — | — |

**Tests.** The Python parser and gate tests ran red before implementation, then **7/7 passed**. The Java nesting, readback-lag and capacity checks also went red to green. All **4 existing** frame-extraction tests passed, and all **8 archived** ABBA windows recomputed exactly.

**Files changed or created**

- Added [build-gpu-profiler.sh](/home/kusutohu/repos/aqualumen/tools/build-gpu-profiler.sh) and `tools/gpu-profiler-mod/{Hooks.java,Targets.java,Timers.java,QueryPolicy.java,QueryPolicyTest.java,fabric.mod.json,gpu-profile.mixins.json}`.
- Changed the existing [frame observer](/home/kusutohu/repos/aqualumen/reports/2026-11-21-animal-light/timing/FrameSample.java), its [build script](/home/kusutohu/repos/aqualumen/reports/2026-11-21-animal-light/timing/build.py), and the [private runner](/home/kusutohu/repos/aqualumen/reports/2026-11-21-lava-light/runtime-v190/run.py).
- Added `README.md`, `run.py`, `profile_data.py`, `test_profile.py`, `calibration_pack.py`, `summarize.py` and `summary.json` under `reports/2026-11-22-gpu-profile/`.
- Added `runs/progress.txt`, `runs/result.json` and, for each calibration attempt, `client.log`, `complete.json`, `frames.csv`, `geometry.json`, `observer.json`, `preflight.json`, `private-game.txt` and `summary.json`. Both accepted-frame CSVs contain only their header. The ignored build directory retains the JARs, calibration ZIP, raw CSVs, bytecode inspection output and driver cache.

**Lab verification passed.** All eight protected file hashes, the Lab metadata digest and the original world contents matched before and after both attempts. Lab still selects 1.8.0 with physics 0.2.0 active and lighting compiler 0.3.0 disabled. The retry monitor flagged its own exiting Java PID once after the exception. The final GPU/process check found zero competing jobs. Release and dist files remained unchanged, and no commit was made. [Lab and process receipt](/home/kusutohu/repos/aqualumen/reports/2026-11-22-gpu-profile/runs/gp-cal-4x-retry/preflight.json)