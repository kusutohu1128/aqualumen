# Minecraft natural-world image validation and frame measurements

Renderer: NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2; driver/GL: 3.2.0 NVIDIA 580.173.02.
Minecraft 1.21.1; Java 21.0.7; installed mods: aqualumen_benchmark 0.3.1, aqualumen_physics 0.2.0, fabric-api-base 0.4.42+6573ed8c19, fabric-block-view-api-v2 1.0.10+6573ed8c19, fabric-key-binding-api-v1 1.0.47+0af3f5a719, fabric-renderer-api-v1 3.4.0+c705a49c19, fabric-rendering-data-attachment-v1 0.3.48+73761d2e19, fabric-rendering-fluids-v1 3.1.6+1daea21519, fabric-resource-loader-v0 1.3.1+5b5275af19, fabricloader 0.19.5, io_github_douira_glsl-transformer 2.0.1, iris 1.8.8+mc1.21.1, java 21, minecraft 1.21.1, mixinextras 0.5.5, org_anarres_jcpp 1.4.14, org_antlr_antlr4-runtime 4.13.1, sodium 0.6.9+mc1.21.1.
Garbage collectors: ZGC Minor Cycles, ZGC Minor Pauses, ZGC Major Cycles, ZGC Major Pauses; initial heap 2048 MiB; maximum heap 6144 MiB.
Runtime cloud settings: Iris pipeline OFF; effective Minecraft mode OFF.
Window and framebuffer: 2560×1440; render distance 12; simulation distance 6; VSync False; frame-limit setting 260.
Pack: `Aqualumen-0.3.1.zip`; SHA-256 `d32ce1763e7b48573c544dba9ae476ea2bf910725cbf365140140a1d1708e856`; active without Iris fallback.
Natural vanilla noise world; seed 308060; UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`; local integrated server with one identified player and no LAN publication.
Requested per scene: 10.0 seconds warmup + 10.0 seconds measurement. Render-loop wall-clock intervals include CPU work, rendering, frame pacing and any chunk work. Screenshots and file serialization occur outside the timed interval.

Camera orientation is locked after input before world rendering; the actual rendered Camera angles and local-player identity are validated for every capture. Fixed-scene player coordinates are also checked.
The accompanying scene PNGs are the visual-review evidence. Frame timings do not score appearance or physical correctness; 16.667 ms is a reference budget, not a quality acceptance threshold.

| Scene | Workload | Frames | Mean FPS | 1% low FPS | P99 ms | Worst ms | Frames >16.67 ms |
|---|---|---:|---:|---:|---:|---:|---:|
| opaque-near-magenta | opaque-occlusion-test | 2595 | 259.5 | 178.3 | 5.25 | 7.76 | 0 |
| opaque-near-lime | opaque-occlusion-test | 2600 | 260.0 | 177.4 | 5.23 | 7.80 | 0 |
| opaque-near-open-magenta | opaque-occlusion-test | 2602 | 260.3 | 179.9 | 5.13 | 6.83 | 0 |
| opaque-near-open-lime | opaque-occlusion-test | 2602 | 260.2 | 186.3 | 5.16 | 5.93 | 0 |
| opaque-far-magenta | opaque-occlusion-test | 2608 | 260.8 | 170.4 | 5.42 | 7.09 | 0 |
| opaque-far-lime | opaque-occlusion-test | 2535 | 253.6 | 161.9 | 5.62 | 8.11 | 0 |
| opaque-far-open-magenta | opaque-occlusion-test | 2541 | 254.0 | 165.0 | 5.63 | 7.88 | 0 |
| opaque-far-open-lime | opaque-occlusion-test | 2540 | 254.0 | 168.1 | 5.62 | 6.55 | 0 |

The 1% low is 1000 divided by the mean of the slowest 1% of intervals; it is not an absolute FPS minimum.
An observed 60 FPS floor requires every measured interval to fit the 16.667 ms budget. A P99 pass allows up to 1% slower frames.

Warmed render views: not measured in this run.
Opaque-occlusion fixtures (8 scenes): exact disposable world, fixture geometry and measured first-person camera eye validated; cleanup confirmed. P99 ≤16.667 ms in every scene: True; every measured frame ≤16.667 ms: True.
These temporary walls and colored targets are artificial test fixtures, not natural-world scenery. The open variants are positive visibility controls; closed variants share white-wall geometry and lighting while changing the hidden background color.
Recorded visual-validation limits: Sequential shots have animated clouds and exposure changes: hidden-color pairs are not pixel-exact evidence of a cloud-radiance leak fix. Open controls test target visibility and closed controls test wall occlusion; the separate production opaque-pixel/cloud-radiance GPU regression is the causal test.
Sequential captures include changing cloud animation and exposure; color pairs are not pixel-exact proof of a depth/leak fix. Review open controls for visible targets and closed walls for occlusion; the separate opaque-pixel/cloud-radiance rendering regression is the causal test.

These are observed results for the recorded configuration, seed, coordinates and durations. They do not guarantee a 60 FPS floor across arbitrary worlds, new chunk generation, mods or background loads. Traversal deliberately visits terrain outside the warmed camera position; it is reported separately from warmed views.
