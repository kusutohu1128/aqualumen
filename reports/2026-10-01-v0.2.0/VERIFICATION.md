# Aqualumen 0.2.0 release verification

2026-10-01 / RTX 3080 Ti 12 GB / NVIDIA 580.173.02 / Ryzen 9 5900X / RAM 48 GB.

This is a working experimental release, not a photorealistic renderer or a complete fluid simulator. Existing user instances and worlds were preserved; all installation and disposable-world testing used the separate **Aqualumen Lab** instance.

## Delivered artifacts

- `dist/Aqualumen-0.2.0.zip`: SHA-256 `be819e6bb54b94ad5306cd60f3b1e839894e656973d54179016bf0f6ca78e794`.
- `dist/aqualumen-physics-0.2.0.jar`: SHA-256 `1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e`.
- Both installed files matched these local build hashes during the completed natural-world run. The archives contain MIT LICENSE and the original shader/client bridge, not the test instrumentation.
- Minecraft 1.21.1 / Fabric Loader 0.19.5 / Iris 1.8.8 / Sodium 0.6.9 / Java 21.0.7. Actual Generational ZGC, initial heap 2 GiB, maximum 6 GiB.

After measurement, the benchmark JAR and its enabling marker were renamed to disabled files (recoverable, not deleted). Normal startup uses a 1600×900 window, 120 FPS cap and pause-on-focus-loss, while keeping 12/6 chunks and the default BALANCED shader. These handoff settings are not substituted for the uncapped 1440p measurement configuration above. F11 can switch to the desktop's fullscreen resolution.

The final uninstrumented launch loaded 17 mods including `aqualumen_physics`, but no `aqualumen_benchmark`; Iris selected the frozen 0.2.0 pack and created the Overworld pipeline. [Actual normal-play debug capture](normal-play-debug.png) confirms 1600×900, RTX 3080 Ti, 12/6 chunks, Java 21.0.7, 6 GiB maximum heap and 120 FPS target (instantaneous counter 118 FPS). `jcmd VM.flags` independently confirmed Generational ZGC and initial/max heap 2/6 GiB. This screenshot is a startup/config smoke check, not an additional FPS-floor measurement.

The initial `intermediary` versus `official` namespace crash was repaired by restoring the missing official `net.fabricmc:intermediary:1.21.1` mapping JAR, verified SHA-256 `6059157dfb4a536ec151697004f74f6004b7d346b289c2f89849e0e585aa36fa`. Subsequent Minecraft/Iris/Sodium launches succeeded. This was a startup mapping problem, not a GPU or shader compile error.

## Actual Minecraft measurements

[Full independently recomputed table, raw CSV, metadata and screenshots](natural/RESULTS.md). Natural vanilla noise Overworld, seed 308060, guarded disposable world UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`. Actual window and framebuffer 2560×1440; render/simulation distances 12/6; BALANCED; VSync off; frame cap set to Minecraft's unlimited selector. Each scene had 20 seconds warmup and 30 seconds sampled render-loop intervals.

| Workload | Observed result | 60 FPS frame-budget result |
|---|---|---|
| 8 warmed views: ocean, shore, river, dusk, night, rain, underwater, rotating camera | Mean 299.8–427.0 FPS; worst frame at most 10.56 ms | Every measured interval within 16.667 ms |
| Real boat contact, scripted 6 m/s translation at 20 Hz | Mean 324.5 FPS; 1% low 124.7 FPS; worst 70.06 ms | 2 of 9,736 intervals exceeded the budget |
| Spectator traversal, scripted 32 m/s translation at 20 Hz | Mean 395.3 FPS; 1% low 122.3 FPS; worst 16.23 ms | Every measured interval within the budget |

**The strict 60 FPS floor across the complete suite was not achieved.** The boat test contains command/network-correction and test-bridge overhead as well as rendering; no measurement isolates the cause of its two outliers. Good mean/P99/1%-low results do not erase those outliers. The traversal path and recorded durations cannot guarantee the same result during arbitrary new chunk generation, complex builds, other mods, or background loads.

The active client contact bridge reported one boat contact and maximum force 8.0 during sampling. This verifies actual contact input, not a calibrated wake profile or manual vanilla rowing performance. Static screenshots alone cannot establish temporal glint/wake stability. [Outlier evidence](BOAT-OUTLIERS.md) also records 3,203 vehicle correction warnings during the scripted boat sample; the causal contribution of correction, logging, GC and rendering was not isolated.

## Additional functional scenes

[Accepted four-scene functional run](functional/RESULTS.md), ten seconds warmup plus ten seconds sampling each: three layers of glass over ocean, Nether, End, then Overworld return. Actual local-player camera, dimensions, framebuffer and frozen pack SHA were checked. Every sampled frame met the 16.667 ms budget; this is a brief smoke check, not the primary 30-second performance suite. Screenshots show the overlapping glass layers with the ocean behind them and dark, dimension-specific environments without the Overworld sun/cloud background.

An earlier three-scene functional attempt recorded its scenes but aborted during final End→Overworld cleanup because the camera still referred to the pre-respawn player for a frame. Its abort evidence is [preserved](rejected/functional-first-aborted.json), and the report tool rejects that incomplete run. The accepted retry explicitly ended in an Overworld scene, letting the existing dimension-transition checks wait before completion. Production shader/physics files and the benchmark JAR were unchanged; the benchmark finishing race remains a known tooling limitation.

[Separate natural cave-water check](cave/RESULTS.md) found a shaded underground pool with measured sky light zero and three air blocks above the water. Ten seconds warmup plus ten seconds sampling: mean 559.2 FPS, worst 5.13 ms, no budget exceedance. Its image shows a dark lush-cave pool without an outdoor sky reflection or bright direct-sun caustic pattern. This one cave does not validate every aquifer, overhang or water-level configuration.

## GPU and reviewer checks

[Actual NVIDIA compile and numerical probe output](glcheck-release.txt): 11 draw-program pairs and 3 compute programs compiled/linked. GPU checks passed for Fresnel reflection, total internal reflection, absorption, solar transmission, wave setup/contact response, maximum-delta CFL stability, integer recenter, damping and teleport reset. Native GL harness checks are separate from Minecraft frame measurements.

[Actual Claude Opus review and dispositions](../../docs/reviews/opus-final-review.md), responding model `claude-opus-5-5`. Source-design review, not independent Minecraft runtime/FPS verification. The completed focused review and sanitized completion evidence are retained; broad timed-out reviews are not treated as completion.

## Visual and physical limits

Actual images show water depth at the shore, underwater attenuation, sunset reflections and playable night exposure without a black shader fallback or missing water geometry. They also retain coarse cloud silhouettes, dense fine water detail, strongly cyan shallows, bright highlight clipping, blue pixelated vanilla rain and an artistic cyan nighttime water baseline. Do not describe the release as photorealistic or radiometrically calibrated.

Contact ripples are a persistent local linear height/velocity wave field, not Minecraft fluid-volume replacement. Fourier wind waves, ray/path approximations and limited caustics are described in [README](../../README.md). Same-height disconnected ponds, flowing-water faces, shoreline topology, multiple water planes, offscreen reflections, cloud volume and full global illumination remain limitations. Large-coordinate multi-minute sailing and every transparency/overlap configuration have not been comprehensively validated.

Failed preflights and interrupted attempts remain locally under the instance's `aqualumen-benchmark/runs/`; they are excluded from the accepted natural-world report. In particular, incorrect-camera early preflights are not substituted for the final guarded measurements.
