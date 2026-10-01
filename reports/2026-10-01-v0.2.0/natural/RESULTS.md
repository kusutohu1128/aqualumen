# Minecraft natural-world frame measurements

Renderer: NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2; driver/GL: 3.2.0 NVIDIA 580.173.02.
Minecraft 1.21.1; Java 21.0.7; installed mods: aqualumen_benchmark 0.2.0, aqualumen_physics 0.2.0, fabric-api-base 0.4.42+6573ed8c19, fabric-block-view-api-v2 1.0.10+6573ed8c19, fabric-key-binding-api-v1 1.0.47+0af3f5a719, fabric-renderer-api-v1 3.4.0+c705a49c19, fabric-rendering-data-attachment-v1 0.3.48+73761d2e19, fabric-rendering-fluids-v1 3.1.6+1daea21519, fabric-resource-loader-v0 1.3.1+5b5275af19, fabricloader 0.19.5, io_github_douira_glsl-transformer 2.0.1, iris 1.8.8+mc1.21.1, java 21, minecraft 1.21.1, mixinextras 0.5.5, org_anarres_jcpp 1.4.14, org_antlr_antlr4-runtime 4.13.1, sodium 0.6.9+mc1.21.1.
Garbage collectors: ZGC Minor Cycles, ZGC Minor Pauses, ZGC Major Cycles, ZGC Major Pauses; initial heap 2048 MiB; maximum heap 6144 MiB.
Runtime cloud settings: Iris pipeline OFF; effective Minecraft mode OFF.
Window and framebuffer: 2560×1440; render distance 12; simulation distance 6; VSync False; frame-limit setting 260 (Minecraft's unlimited selector).
Pack: `Aqualumen-0.2.0.zip`; SHA-256 `be819e6bb54b94ad5306cd60f3b1e839894e656973d54179016bf0f6ca78e794`; active without Iris fallback.
Natural vanilla noise world; seed 308060; UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`; local integrated server with one identified player and no LAN publication.
Requested per scene: 20.0 seconds warmup + 30.0 seconds measurement. Render-loop wall-clock intervals include CPU work, rendering, frame pacing and any chunk work. Screenshots and file serialization occur outside the timed interval.

Camera orientation is locked after input before world rendering; the actual rendered Camera angles and local-player identity are validated for every capture. Fixed-scene player coordinates are also checked.

| Scene | Workload | Frames | Mean FPS | 1% low FPS | P99 ms | Worst ms | Frames >16.67 ms |
|---|---|---:|---:|---:|---:|---:|---:|
| ocean-day | warmed-view | 9769 | 325.7 | 186.1 | 4.90 | 7.04 | 0 |
| coast-day | warmed-view | 9863 | 328.8 | 192.1 | 4.80 | 10.56 | 0 |
| river-day | warmed-view | 10566 | 352.2 | 199.6 | 4.59 | 7.60 | 0 |
| ocean-dusk | warmed-view | 9746 | 324.9 | 186.5 | 4.87 | 9.98 | 0 |
| ocean-night | warmed-view | 10211 | 340.4 | 194.6 | 4.70 | 7.29 | 0 |
| ocean-rain | warmed-view | 8994 | 299.8 | 174.6 | 5.12 | 8.42 | 0 |
| underwater | warmed-view | 12811 | 427.0 | 229.9 | 3.93 | 10.19 | 0 |
| moving-view | warmed-view | 9938 | 331.3 | 190.2 | 4.75 | 7.33 | 0 |
| boat-contact | scripted-boat-contact | 9736 | 324.5 | 124.7 | 5.43 | 70.06 | 2 |
| chunk-traversal | chunk-traversal | 11858 | 395.3 | 122.3 | 6.34 | 16.23 | 0 |

The 1% low is 1000 divided by the mean of the slowest 1% of intervals; it is not an absolute FPS minimum.
An observed 60 FPS floor requires every measured interval to fit the 16.667 ms budget. A P99 pass allows up to 1% slower frames.

Warmed render views (8 scenes): P99 ≤16.667 ms in every scene: True; every measured frame ≤16.667 ms: True.
Scripted boat contact (1 scene): P99 ≤16.667 ms: True; every measured frame ≤16.667 ms: False; total over-budget frames: 2.
Chunk traversal (1 scene): P99 ≤16.667 ms in every scene: True; every measured frame ≤16.667 ms: True.
Traversal uses spectator teleports at 32 m/s and 20 Hz, so the measured workload includes scripted command/network correction overhead as well as chunk work; it is not a manual walking/flight benchmark.
Boat-contact bridge was active during measurement: True; maximum simultaneous contacts 1; maximum force 8.000. The boat follows a scripted 6 m/s path; this validates contact input rather than player-controlled vanilla rowing.

These are observed results for the recorded configuration, seed, coordinates and durations. They do not guarantee a 60 FPS floor across arbitrary worlds, new chunk generation, mods or background loads. Traversal deliberately visits terrain outside the warmed camera position; it is reported separately from warmed views.
