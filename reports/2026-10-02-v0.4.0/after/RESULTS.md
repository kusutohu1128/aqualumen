# Minecraft natural-world image validation and frame measurements

Renderer: NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2; driver/GL: 3.2.0 NVIDIA 580.173.02.
Minecraft 1.21.1; Java 21.0.7; installed mods: aqualumen_benchmark 0.3.3, aqualumen_physics 0.2.0, fabric-api-base 0.4.42+6573ed8c19, fabric-block-view-api-v2 1.0.10+6573ed8c19, fabric-key-binding-api-v1 1.0.47+0af3f5a719, fabric-renderer-api-v1 3.4.0+c705a49c19, fabric-rendering-data-attachment-v1 0.3.48+73761d2e19, fabric-rendering-fluids-v1 3.1.6+1daea21519, fabric-resource-loader-v0 1.3.1+5b5275af19, fabricloader 0.19.5, io_github_douira_glsl-transformer 2.0.1, iris 1.8.8+mc1.21.1, java 21, minecraft 1.21.1, mixinextras 0.5.5, org_anarres_jcpp 1.4.14, org_antlr_antlr4-runtime 4.13.1, sodium 0.6.9+mc1.21.1.
Garbage collectors: ZGC Minor Cycles, ZGC Minor Pauses, ZGC Major Cycles, ZGC Major Pauses; initial heap 2048 MiB; maximum heap 6144 MiB.
Runtime cloud settings: Iris pipeline OFF; effective Minecraft mode OFF.
Window and framebuffer: 2560×1440; render distance 12; simulation distance 6; VSync False; frame-limit setting 260.
Pack: `Aqualumen-0.4.0.zip`; SHA-256 `5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069`; active without Iris fallback.
Natural vanilla noise world; seed 308060; UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`; local integrated server with one identified player and no LAN publication.
Requested per scene: 5.0 seconds warmup + 5.0 seconds measurement. Render-loop wall-clock intervals include CPU work, rendering, frame pacing and any chunk work. Screenshots and file serialization occur outside the timed interval.

Camera orientation is locked after input before world rendering; the actual rendered Camera angles and local-player identity are validated for every capture. Fixed-scene player coordinates are also checked.
The accompanying scene PNGs are the visual-review evidence. Frame timings do not score appearance or physical correctness; 16.667 ms is a reference budget, not a quality acceptance threshold.

| Scene | Workload | Frames | Mean FPS | 1% low FPS | P99 ms | Worst ms | Frames >16.67 ms |
|---|---|---:|---:|---:|---:|---:|---:|
| coast-day | warmed-view | 798 | 159.6 | 117.0 | 8.21 | 9.03 | 0 |
| river-day | warmed-view | 804 | 160.9 | 122.4 | 8.06 | 8.60 | 0 |
| ocean-day | warmed-view | 680 | 136.1 | 90.9 | 10.19 | 14.85 | 0 |
| ocean-dusk | warmed-view | 680 | 136.1 | 90.1 | 9.78 | 17.09 | 1 |
| ocean-night | warmed-view | 715 | 143.1 | 90.7 | 9.24 | 21.78 | 1 |
| ocean-rain | warmed-view | 630 | 126.0 | 92.9 | 10.55 | 11.15 | 0 |
| underwater | warmed-view | 780 | 156.1 | 113.7 | 8.57 | 9.05 | 0 |
| underwater-up-near | warmed-view | 960 | 192.1 | 135.4 | 7.09 | 7.75 | 0 |
| underwater-up-deep | warmed-view | 941 | 188.3 | 133.3 | 7.15 | 8.08 | 0 |
| underwater-up-tilt | warmed-view | 966 | 193.3 | 137.9 | 6.94 | 8.86 | 0 |
| moving-view | warmed-view | 683 | 136.6 | 101.0 | 9.52 | 10.50 | 0 |
| boat-contact | scripted-boat-contact | 663 | 132.6 | 84.0 | 10.22 | 14.76 | 0 |
| cave-water | warmed-view | 808 | 161.7 | 109.7 | 8.74 | 10.34 | 0 |
| glass-layers | warmed-view | 748 | 149.7 | 91.4 | 9.95 | 15.26 | 0 |
| nether-view | warmed-view | 1875 | 375.2 | 233.9 | 3.99 | 4.70 | 0 |
| end-view | warmed-view | 1886 | 377.3 | 230.1 | 4.02 | 4.75 | 0 |

The 1% low is 1000 divided by the mean of the slowest 1% of intervals; it is not an absolute FPS minimum.
An observed 60 FPS floor requires every measured interval to fit the 16.667 ms budget. A P99 pass allows up to 1% slower frames.

Warmed render views (15 scenes): P99 ≤16.667 ms in every scene: True; every measured frame ≤16.667 ms: False.
Scripted boat contact (1 scene): P99 ≤16.667 ms: True; every measured frame ≤16.667 ms: True; total over-budget frames: 0.
Boat-contact bridge was active during measurement: True; maximum simultaneous contacts 1; maximum force 0.221. The boat follows a scripted 6 m/s path; this validates contact input rather than player-controlled vanilla rowing.

These are observed results for the recorded configuration, seed, coordinates and durations. They do not guarantee a 60 FPS floor across arbitrary worlds, new chunk generation, mods or background loads. Traversal deliberately visits terrain outside the warmed camera position; it is reported separately from warmed views.
