**Preview 8 completed all four ABBA runs without crossing either investigation threshold.** Across the two scenes, its largest paired increase was **1.96% in mean frame interval** and **6.66% in p99**, below the respective 5% and 10% thresholds. No retry or pair c was needed. Preview 8 remains unpublished. [Results report](/home/kusutohu/repos/aqualumen/reports/2026-11-22-eye-adaptation/README.md) · [Raw intervals and paired results](/home/kusutohu/repos/aqualumen/reports/2026-11-22-eye-adaptation/frame-times.json)

### Minecraft frame timings

RTX 3080 Ti, 2560×1440, 12 chunks, VSync off, 120 FPS cap. Each scene contributed 10 seconds of consecutive render-return intervals. I independently recomputed all eight windows and all paired deltas from 4,222 intervals.

| Run, in order | both-west FPS | Mean ms | p99 ms | day-white FPS | Mean ms | p99 ms |
|---|---:|---:|---:|---:|---:|---:|
| `eye-frames-p7-a` | 38.58 | 25.919 | 28.524 | 66.82 | 14.965 | 17.627 |
| `eye-frames-p8-a` | 38.38 | 26.052 | 30.423 | 66.60 | 15.014 | 17.632 |
| `eye-frames-p8-b` | 38.82 | 25.762 | 27.967 | 66.13 | 15.122 | 17.857 |
| `eye-frames-p7-b` | 38.91 | 25.700 | 28.711 | 67.42 | 14.832 | 17.539 |

| Paired 8−7 | Scene | Δ FPS | Δ mean ms | Δ p99 ms |
|---|---|---:|---:|---:|
| a | both-west · night, two lamps | −0.197 | +0.133 (+0.51%) | +1.899 (+6.66%) |
| a | day-white · noon, open roof | −0.218 | +0.049 (+0.33%) | +0.005 (+0.03%) |
| b | both-west · night, two lamps | −0.095 | +0.063 (+0.24%) | −0.744 (−2.59%) |
| b | day-white · noon, open roof | −1.296 | +0.291 (+1.96%) | +0.318 (+1.81%) |

Night p99 changed direction when the run order reversed. These measurements cover the two fixed scenes. The cave walk provides separate evidence for the exposure change.

### Startup and cache

Launch timestamps have one-second resolution. The first observer return can occur on a loading screen. The overworld column identifies the first render return after the terrain workers started.

| Run | Private driver cache at launch | First observer return | First overworld render | Runner confirmed scene |
|---|---|---:|---:|---:|
| p7-a | Empty | ~15.6 s | ~295.5 s | 297 s |
| p8-a | Populated by p7-a, first use by p8 | ~14.4 s | ~19.7 s | 22 s |
| p8-b | Previously used by p8 | ~14.8 s | ~19.9 s | 22 s |
| p7-b | Previously used by both packs | ~15.6 s | ~20.8 s | 23 s |

Preview 8 cold-start time remains unmeasured. Before every probe and game run, I checked `nvidia-smi` and `ps`. Jobs ran serially. Across 151 in-run samples, the GPU monitor observed only the existing desktop processes and the private client.

### Tests and probes

- **Red → green:** All four CPU tests initially errored on the unsupported `pack_path` argument. All four passed after implementation, covering staged-pack acceptance, same-name ZIP substitution, missing `STILL`, and a truncated sample. The legacy call reproduced preview 7’s published night and day timings.
- **Archive identity:** The rebuilt preview 8 ZIP matched the staged candidate byte-for-byte. Of 138 entries shared with preview 7, only the three expected shaders differed.
- **GPU correctness:** All three commands exited 0. Harness timings were excluded from the Minecraft tables.

| Probe | Renderer | GL version |
|---|---|---|
| `make check-eye` | `NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2` | `4.6.0 NVIDIA 580.173.02` |
| Unpacked preview 8 `--play-release` | `NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2` | `4.6.0 NVIDIA 580.173.02` |
| Unpacked preview 8 `--eye-exposure-probe` | `llvmpipe (LLVM 20.1.2, 256 bits)` | `4.5 (Compatibility Profile) Mesa 25.2.8-0ubuntu0.24.04.2` |

**Lab was unchanged.** All five protected file hashes, the disabled compiler hash, active mod list, and selected 1.8.0 pack matched preflight. The 10,639-entry Lab metadata inventory matched, and every run verified the original world contents. Preview 8 is absent from both `dist/` and Lab. No git commit or push was made.

### Files changed or created

The inventory below covers all **68 persistent workspace files**, including ignored captures and cache files. `T` is [reports/2026-11-21-animal-light](/home/kusutohu/repos/aqualumen/reports/2026-11-21-animal-light) and `R` is [reports/2026-11-22-eye-adaptation](/home/kusutohu/repos/aqualumen/reports/2026-11-22-eye-adaptation).

| Location | Files |
|---|---|
| Modified tracked files | `T/timing/measure.py`, `T/progress.txt`, `T/result.json`, `R/README.md` |
| Created under `R/` | `frame_times.py`, `test_frame_times.py`, `frame-times.json`, `timing-check-eye-nvidia.log`, `timing-play-release-nvidia.log`, `timing-eye-mesa.log` |
| Created in **each** of the four `T/<run-label>/` directories | `client.log`, `complete.json`, `geometry.json`, `observer.json`, `preflight.json`, `private-game.txt`, `both-west-ingame.png`, `both-west-x11-a.png`, `both-west-x11-b.png`, `day-white-ingame.png`, `day-white-x11-a.png`, `day-white-x11-b.png` |
| `T/eye-frames-p7-a/f2/` | `2026-11-22_03.14.15.png`, `2026-11-22_03.14.49.png` |
| `T/eye-frames-p8-a/f2/` | `2026-11-22_03.15.42.png`, `2026-11-22_03.16.16.png` |
| `T/eye-frames-p8-b/f2/` | `2026-11-22_03.17.09.png`, `2026-11-22_03.17.43.png` |
| `T/eye-frames-p7-b/f2/` | `2026-11-22_03.18.37.png`, `2026-11-22_03.19.11.png` |
| `build/eye-adaptation/timing-glcache/GLCache/d11dcff50d07dfe9a860932261446f34/b66383c74676460a/` | `bf70260d41c7b5cd.bin`, `bf70260d41c7b5cd.toc` |