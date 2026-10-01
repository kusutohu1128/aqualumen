# Aqualumen 0.3.0 visual-quality release verification

2026-10-01 / RTX 3080 Ti 12 GB / NVIDIA 580.173.02 / Ryzen 9 5900X / RAM 48 GB.

This is a usable experimental rendering checkpoint, not a photorealistic renderer or a complete fluid simulator. The user explicitly relaxed the original 60 FPS floor: visual quality is the priority, frame timings are observations rather than the release gate. Existing user instances/worlds were preserved; installation and disposable-world tests are confined to **Aqualumen Lab**.

## Frozen artifacts and configuration

- Shader `dist/Aqualumen-0.3.0.zip`: SHA-256 `2d4d16d356ea1728a35b4e3933da79dd98627e5de47f7bfbd161c359ad09f0f1`. Rebuilding the ZIP reproduces this hash; installed ZIP matches.
- Unchanged production contact Mod `dist/aqualumen-physics-0.2.0.jar`: SHA-256 `1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e`.
- Test-only benchmark 0.3.0 installed JAR: SHA-256 `a60afaa8ebd6d31dcd5788035fe20234c85047d670afa7d69f17e063711cf1d5`. A later rebuilt container has different ZIP timestamps; its `Recorder.class` has the same SHA-256 `6043c7c9361c4c5add85d332c153b79b2dfe8a14c960e7ed6785ab613d504710`. It is not a production dependency.
- Minecraft 1.21.1 / Fabric Loader 0.19.5 / Iris 1.8.8 / Sodium 0.6.9 / Java 21.0.7. Actual Generational ZGC; initial/max heap 2/6 GiB.
- Review captures: actual 2560×1440 window/framebuffer, render/simulation 12/6 chunks, BALANCED, VSync off, unlimited selector. Natural vanilla noise world, seed 308060, UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`; local-player identity and rendered camera checked. Built-in Minecraft clouds are OFF because the pack renders its own volume clouds.

## Actual Minecraft review runs

[Main ten-scene raw CSV, metadata and captures](natural/RESULTS.md): `quality-v0.3-main`, ten seconds warmup and ten seconds sampling per scene. All 17,598 sampled render-loop intervals were below the 16.667 ms reference budget; this is not a minimum-FPS guarantee. Eight warmed views averaged 162.8–191.6 FPS. Scripted boat contact averaged 169.6 FPS with worst 11.27 ms; scripted traversal averaged 186.3 FPS with worst 13.89 ms. Timed samples exclude PNG writing/serialization.

The moving boat bridge was active with at least one contact and maximum force 8.0. Boat movement uses scripted 6 m/s teleports at 20 Hz, not manual vanilla rowing; traversal uses scripted 32 m/s spectator movement. Correction/chunk work is included, and no causal isolation or calibrated wake profile is claimed. Shorter 0.3 sampling and new clouds mean this is not an apples-to-apples performance comparison with 0.2's 30-second samples.

Root reviewed final-build ocean, coast, dusk, night, rain and underwater captures. The ocean has calmer broader highlights; dusk retains warm cloud/water reflections; night is dark rather than a bright cyan water baseline; rain dims the sky and sea but preserves vanilla rain-particle appearance. Underwater attenuation shows faint seabed/plants rather than a black shader fallback. The coast remains strongly turquoise as explicitly noted below. PNGs cannot prove temporal shimmer/wake stability.

[Three-scene functional run](functional/RESULTS.md), `quality-v0.3-functional`, 10+10 seconds per scene: overlapping glass, Nether, then End. Glass and the dimension-specific dark environments rendered without the Overworld cloud/sun background. The run deliberately ended in End: the client returned to the local Overworld player/camera and passed the unchanged strict guard before completion, verifying the benchmark finisher fix in Minecraft without the earlier extra-Overworld-scene workaround.

Glass averaged 169.4 FPS; Nether 599.1; End 648.8. End included **one 61.46 ms frame**; it is retained in the CSV and is not erased by the high mean/P99. Its cause was not isolated, and no complete-suite minimum-60-FPS claim is made.

[Separate cave-water run](cave/RESULTS.md), `quality-v0.3-cave`, 10+10 seconds: 2,333 measured intervals, mean 233.4 FPS, P99 6.064 ms, worst 7.695 ms, zero reference-budget exceedances. The cave discovery requires sky light zero above the pool; the screenshot shows a shaded lush-cave pool without a bright outdoor sky reflection. No separate numerical skylight field was serialized, and this one pool does not validate every aquifer/overhang configuration.

All 79 accepted raw/report files were copied byte-for-byte and independently reloaded from the repository report directories. Functional scenes contain 14,171 measured intervals, with the single End outlier. Boat diagnostics contain 11 active/contact snapshots, 10 with nonzero force. Only final frozen-hash runs are copied into the accepted directories.

## Implemented changes

Water scattering now depends on incoming sky/sun/moon/block illumination instead of a constant cyan source. Fine wind-wave slopes are dissipated/filtered, unresolved variance moves into reflection roughness, GGX glints are numerically stable, SSR hits are refined, and finite-width caustic focus is regularized. Fresnel, Snell, TIR and the selected RGB extinction coefficients remain intact.

Above-water refraction initialization uses local vertical depth and the downward refracted ray. The tracer only publishes a converged depth intersection; later offscreen/foreground failure preserves the original UV and initial optical path, rather than a stale unconverged receiver. This remains a screen-space approximation, not offscreen geometry or a bathymetry map.

Clouds now integrate filtered 3D density through a curved 1450–2200 m layer, using 32 view segments and 6 light-occlusion segments. The sky LUT is 1024×512, with explicit longitude wrap, bilinear reconstruction and solar-row exclusion. Cloud shadows shared with ground/water are camera-local; atmosphere/volume multiple scattering is approximated. HDR output uses a shared RGB soft shoulder rather than independently hard-clipping bright channels.

## GPU regressions and actual Sonnet implementation

[Actual NVIDIA compilation and numerical output](glcheck-release.txt): all 11 draw pairs and 3 compute programs passed. Checks cover dielectric reflection/TIR/absorption, 1 m shore Snell initialization (1.51234 m versus 20 m grazing distance), non-emitting water scatter, solar column, sky lookup/wrap/cache row, HDR16/HDR64 distinction, persistent wave setup/contact/CFL/recenter/damping/reset, and the production refraction tracer on controlled depth textures.

Tests were added before the corresponding fixes. The old display collapsed HDR16 and HDR64 to white; the new output remains distinct (0.97282 / 0.992977). The old tracer leaked a stale 0.947753 m path after a later offscreen iterate; the new one retains its 0.3 m fallback and still accepts a converged 1 m hit. Native harness tests do not establish Minecraft FPS or physical realism.

[Actual Claude Sonnet contributions](../../docs/reviews/sonnet-v0.3-implementation.md) and sanitized model evidence identify three successful no-tools turns responding as `claude-sonnet-5-5`: cloud angular footprint, shallow refraction seed, and converged trace commit. Codex reviewed/adapted the generated patches and ran GPU/game verification. Sonnet did not run Minecraft. The earlier Opus review applies to 0.2 architecture, not independent approval of this release.

[Benchmark finisher regression output](benchmark-regressions.txt) covers delayed End→Overworld respawn, stale camera, absent player, timeout and unchanged strict identity guard. This logic regression is separate from the real dimension-transition test.

## Normal-play handoff

After measurement the test JAR and its enabling marker were renamed to disabled files, preserved rather than deleted. A fresh launch loaded 17 mods including physics 0.2.0, **no benchmark Mod**, selected the frozen 0.3 ZIP and created the Overworld pipeline without shader fallback. The stale benchmark `status.json` describes the earlier test client's quit, not this uninstrumented client.

Normal settings are restored to 1600×900 window, 120 FPS cap, pause on lost focus, 12/6 chunks and BALANCED. [Actual debug screenshot](normal-play-debug.png) confirms RTX 3080 Ti, NVIDIA driver, resolution, chunks, Java 21.0.7, 6 GiB heap, 120 target and a 118 FPS instantaneous counter. `jcmd VM.flags` independently confirms Generational ZGC and initial/max heap 2/6 GiB. This is a configuration/startup smoke check, not another uncapped FPS benchmark. The disposable test world was saved and returned to the title menu for handoff.

The prior mapping namespace launch failure remains repaired; the exact missing Intermediary artifact and repair evidence are retained in the [0.2 startup report](../2026-10-01-v0.2.0/VERIFICATION.md). Offline account-property 401 messages during these deliberately offline launches are not shader compile failures; no account credentials or launcher command lines are included in the reports.

## Visual limitations and excluded preflights

The visual target is improved, not finished: shallow coastal water still has strongly turquoise regions and sharp refraction/reflection boundaries. Fixing the measured path bugs did **not** prove that this appearance was solved. Offscreen fallback colors may not correspond to the Snell-ray endpoint; near a bank the view-ray receiver can yield zero local depth. No full seabed reconstruction, GI, TAA, radiometric calibration or temporal shimmer guarantee is provided. Cloud shapes remain procedural and can look layered/soft; rain retains pixelated vanilla particles; moon lighting assumes a fixed full moon.

The unchanged contact field is local linear height/velocity simulation, not water-mass transport, buoyancy replacement or Navier–Stokes. Same-height disconnected ponds, shoreline topology, flowing faces, multiple water planes and long-distance sailing remain incompletely validated.

Read-only source audit also identified two inherited 0.2 hazards: `waterCaustic` computes fragment derivatives after a varying-depth early return, and above-water caustics have no explicit Earth-dimension gate. Neither is introduced by this release or established as the turquoise-shore cause. The Nether/End smoke captures do not validate water caustics placed in those dimensions. These remain follow-up work, not silently claimed as fixed by passing compilation.

Earlier `quality-v0.3-smoke` (hash `c6c90d40…`) and `quality-v0.3-refined-smoke` (`beef9672…`) are preflights, not accepted final-build results. Their tested ZIPs and logs are preserved locally under ignored `build/snapshots/` and the isolated instance. The final-hash coast-only five-second smoke is also not substituted for the full suite. Historical 0.1/0.2 reports remain version-specific and are not used to infer the new volume-cloud performance.
