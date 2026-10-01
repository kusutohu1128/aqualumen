# Minecraft natural-world image validation and frame measurements

Renderer: NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2; driver/GL: 3.2.0 NVIDIA 580.173.02.
Minecraft 1.21.1; Java 21.0.7; installed mods: aqualumen_benchmark 0.3.2, aqualumen_physics 0.2.0, fabric-api-base 0.4.42+6573ed8c19, fabric-block-view-api-v2 1.0.10+6573ed8c19, fabric-key-binding-api-v1 1.0.47+0af3f5a719, fabric-renderer-api-v1 3.4.0+c705a49c19, fabric-rendering-data-attachment-v1 0.3.48+73761d2e19, fabric-rendering-fluids-v1 3.1.6+1daea21519, fabric-resource-loader-v0 1.3.1+5b5275af19, fabricloader 0.19.5, io_github_douira_glsl-transformer 2.0.1, iris 1.8.8+mc1.21.1, java 21, minecraft 1.21.1, mixinextras 0.5.5, org_anarres_jcpp 1.4.14, org_antlr_antlr4-runtime 4.13.1, sodium 0.6.9+mc1.21.1.
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
| air-shadow-backlit | air-sun-shadow-test | 2619 | 261.9 | 172.4 | 5.41 | 9.83 | 0 |
| air-sunlit-front | air-sun-shadow-test | 2456 | 245.6 | 160.4 | 5.87 | 7.44 | 0 |
| air-backlit-open | air-sun-shadow-test | 2590 | 259.0 | 172.8 | 5.40 | 7.66 | 0 |

The 1% low is 1000 divided by the mean of the slowest 1% of intervals; it is not an absolute FPS minimum.
An observed 60 FPS floor requires every measured interval to fit the 16.667 ms budget. A P99 pass allows up to 1% slower frames.

Warmed render views: not measured in this run.
West-facing air-shadow fixtures (3 scenes): exact approved receiver/target planes, first-person eye and frozen client/server sun times validated; cleanup confirmed.
These artificial WHITE concrete receivers occupy X432/Y157..165/Z-387..-379; magenta targets occupy X426/Y158..164/Z-386..-380, with identical sea-lantern upper corners. Camera/player is (448.5,160,-383.5), yaw90/pitch0. The 11000 backlit and 1000 front-lit sun angles are approximately opposed controls, not an exact matched-exposure radiometric experiment.
air-shadow-backlit: white receiver present=True; requested/client/server time=11000/11000/11000; 130 placed cells in 130 prechecked AIR cells.
air-sunlit-front: white receiver present=True; requested/client/server time=1000/1000/1000; 130 placed cells in 130 prechecked AIR cells.
air-backlit-open: white receiver present=False; requested/client/server time=11000/11000/11000; 49 placed cells in 130 prechecked AIR cells.
Review directional illumination and shadowing, with the open variant confirming the target is visible. A receiver may be partially sunlit; indirect sky illumination and atmospheric fog remain valid on shaded faces. Do not require the entire image, fog or shadow to be black. Animated clouds and exposure evolution also forbid a pixel-exact sequential-difference causal claim.
Recorded visual-validation limits: Sequential shots have animated clouds and exposure changes: hidden-color pairs are not pixel-exact evidence of a cloud-radiance leak fix. Open controls test target visibility and closed controls test wall occlusion; the separate production opaque-pixel/cloud-radiance GPU regression is the causal test. West-facing backlit/front-lit controls use approximately opposed sun times11000/1000: partial receiver illumination, indirect sky light and atmospheric fog are valid; do not demand an all-black shadow.

These are observed results for the recorded configuration, seed, coordinates and durations. They do not guarantee a 60 FPS floor across arbitrary worlds, new chunk generation, mods or background loads. Traversal deliberately visits terrain outside the warmed camera position; it is reported separately from warmed views.
