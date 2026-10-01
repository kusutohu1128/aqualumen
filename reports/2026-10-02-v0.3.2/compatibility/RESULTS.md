# Minecraft natural-world image validation and frame measurements

Renderer: NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2; driver/GL: 3.2.0 NVIDIA 580.173.02.
Minecraft 1.21.1; Java 21.0.7; installed mods: aqualumen_benchmark 0.3.2, aqualumen_physics 0.2.0, fabric-api-base 0.4.42+6573ed8c19, fabric-block-view-api-v2 1.0.10+6573ed8c19, fabric-key-binding-api-v1 1.0.47+0af3f5a719, fabric-renderer-api-v1 3.4.0+c705a49c19, fabric-rendering-data-attachment-v1 0.3.48+73761d2e19, fabric-rendering-fluids-v1 3.1.6+1daea21519, fabric-resource-loader-v0 1.3.1+5b5275af19, fabricloader 0.19.5, io_github_douira_glsl-transformer 2.0.1, iris 1.8.8+mc1.21.1, java 21, minecraft 1.21.1, mixinextras 0.5.5, org_anarres_jcpp 1.4.14, org_antlr_antlr4-runtime 4.13.1, sodium 0.6.9+mc1.21.1.
Garbage collectors: ZGC Minor Cycles, ZGC Minor Pauses, ZGC Major Cycles, ZGC Major Pauses; initial heap 2048 MiB; maximum heap 6144 MiB.
Runtime cloud settings: Iris pipeline OFF; effective Minecraft mode OFF.
Window and framebuffer: 2560×1440; render distance 12; simulation distance 6; VSync False; frame-limit setting 260.
Pack: `Aqualumen-0.3.2.zip`; SHA-256 `7b5bdfb78e79b3214ca2a1fca77657c88680dbf46ef1b875dd95c0eeb652a9c2`; active without Iris fallback.
Natural vanilla noise world; seed 308060; UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`; local integrated server with one identified player and no LAN publication.
Requested per scene: 5.0 seconds warmup + 5.0 seconds measurement. Render-loop wall-clock intervals include CPU work, rendering, frame pacing and any chunk work. Screenshots and file serialization occur outside the timed interval.

Camera orientation is locked after input before world rendering; the actual rendered Camera angles and local-player identity are validated for every capture. Fixed-scene player coordinates are also checked.
The accompanying scene PNGs are the visual-review evidence. Frame timings do not score appearance or physical correctness; 16.667 ms is a reference budget, not a quality acceptance threshold.

| Scene | Workload | Frames | Mean FPS | 1% low FPS | P99 ms | Worst ms | Frames >16.67 ms |
|---|---|---:|---:|---:|---:|---:|---:|
| ocean-day | warmed-view | 866 | 173.3 | 119.4 | 7.91 | 9.25 | 0 |
| coast-day | warmed-view | 845 | 169.1 | 119.2 | 7.80 | 10.25 | 0 |
| ocean-dusk | warmed-view | 863 | 172.6 | 122.4 | 7.59 | 9.68 | 0 |
| ocean-night | warmed-view | 900 | 180.1 | 130.0 | 7.33 | 8.54 | 0 |
| ocean-rain | warmed-view | 787 | 157.6 | 117.2 | 8.27 | 9.58 | 0 |
| underwater | warmed-view | 1000 | 200.1 | 138.2 | 6.62 | 7.97 | 0 |
| cave-water | warmed-view | 1061 | 212.2 | 145.9 | 6.33 | 7.45 | 0 |
| glass-layers | warmed-view | 848 | 169.7 | 114.8 | 8.15 | 9.90 | 0 |
| nether-view | warmed-view | 3322 | 664.5 | 338.0 | 2.68 | 3.96 | 0 |
| end-view | warmed-view | 3267 | 653.4 | 328.6 | 2.61 | 5.00 | 0 |

The 1% low is 1000 divided by the mean of the slowest 1% of intervals; it is not an absolute FPS minimum.
An observed 60 FPS floor requires every measured interval to fit the 16.667 ms budget. A P99 pass allows up to 1% slower frames.

Warmed render views (10 scenes): P99 ≤16.667 ms in every scene: True; every measured frame ≤16.667 ms: True.

These are observed results for the recorded configuration, seed, coordinates and durations. They do not guarantee a 60 FPS floor across arbitrary worlds, new chunk generation, mods or background loads. Traversal deliberately visits terrain outside the warmed camera position; it is reported separately from warmed views.
