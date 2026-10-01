# Aqualumen 0.3.2 — finite local aerial scattering

## Scope and cause

The user supplied a screenshot of grass/dirt appearing veiled by sunlight. Terrain still has its block texture: the symptom need not be actual alpha transparency. The 0.3.1 cloud-buffer fix did not address the separate forward solar aureole in the cloud-free sky LUT. Its composite still mixed a kilometres-long sky ray into every short foreground air segment, independently of the segment's shadows, then added a second shadow-sampled shaft term. Out-of-coverage volume shadow samples also defaulted to fully lit.

A controlled production-composite regression reproduced that unwanted dependency on the actual RTX 3080 Ti. With an opaque 0.05 RGB surface at 8.24621 m, fully blocked in-coverage shadows, fixed diffuse illumination and fixed direct-solar cache, changing only a 10-degree forward sky cone by +4 changed red from **0.0496061 to 0.0889926** (largest RGB leak **0.0393865**). It failed before the shader edit. With 0.3.2, both outputs are **0.0499892**, difference **0**, alpha **1**. This is controlled causal evidence, not an exact replay of the user's screenshot.

## Implementation

- Integrate only the finite camera-to-first-depth segment, with RGB Rayleigh/Mie scattering and Beer–Lambert extinction. Reuse the sky coefficients: `BETA_R=(5.8e-6,13.5e-6,33.1e-6)` and `BETA_M=2.1e-5` per Minecraft metre; aerosol extinction is `1.1*BETA_M`.
- Each piecewise-constant interval uses the analytic weight `(1-exp(-sigma_t*ds))/sigma_t` and accumulated eye transmittance. A small-optical-depth series avoids float cancellation. Zero distance or zero haze density is the identity.
- Direct scattering uses the shared cloud-attenuated solar cache and each interval's shadow visibility. It is not the directional sky image and has no surface cosine factor.
- Shadow coverage that is unknown suppresses only the volume-direct term, with a smooth distance edge. Surface shadows are unchanged; legitimate diffuse light is not blacked out.
- Approximate ambient light uses the five-direction cloud-free sky irradiance divided by `2*pi`, an isotropized upper-hemisphere closure. Sky exposure gates ambient only, not air density or genuine sunlit openings.
- Samples start at `relativeWorld(vec3(0))`, not at the coordinate origin. Iris's named player/feet space is head-relative; this is **not a fixed 1.62 m eye-height correction**.
- Underwater optics, terrain opacity, water coefficients, waves, clouds, and the physics Mod are unchanged. Nether/End retain their simple non-Earth fog.

## Native GPU verification

[Initial RED](native/foreground-haze-red.txt), [initial GREEN](native/foreground-haze-green.txt), [final targeted tests](native/foreground-haze-final.txt) and [full check](native/full-check.txt) are saved. Renderer is `NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2`, OpenGL `4.6.0 NVIDIA 580.173.02`; no software renderer is accepted by the targeted probe. These runs finished before any timed Minecraft A/B scenes; GPU harness output is not Minecraft performance.

All 11 graphics program pairs and the three compute shaders compile/link. Existing water/refraction/scattering, sky LUT, tone mapping, wave-field, MRT and 16/64/128 m cloud-leak regressions pass unchanged. New production-composite tests also pass:

- Fully blocked forward-sky cone: RGB difference zero, alpha one.
- Covered sunlit segment: positive direct gain `0.00764352..0.00771025`; zero solar cache returns to ambient/extinction only, `0.0499892` red.
- Independent double-precision homogeneous-air analytic reference: largest RGB error `4.48934e-08`.
- Unknown shadow coverage: same ambient/extinction-only result, not an invented fully-lit fallback.
- Zero distance and public `HAZE_DENSITY=0`: input 0.05 RGB is preserved with finite output.
- Consistent horizontal eye/shadow/absolute-coordinate rebasing: illuminated red remains `0.0576703`.

The analytic fixture is a short, homogeneous, optically thin path; the covariance case is horizontal. These do not establish long-path integration accuracy, real shadow-map generation, vertical rebasing, calibrated radiometry or screenshot identity. Real-world compatibility evidence is separate below.

## Isolated Minecraft validation

The [old 0.3.1 air controls](before/RESULTS.md) use the exact installed historical ZIP, new benchmark 0.3.2, and three approved west-facing fixtures. Requested, client and server times agree: backlit 11000, front-lit 1000, open backlit 11000. All captures have first-person eye/camera agreement, 2560x1440 window/framebuffer, the exact dedicated `AqualumenNaturalV2` UUID/seed 308060, one offline test actor and no LAN server.

An initial attempt at 1600x900 was rejected by the resolution guard before run initialization or fixture placement; it is not accepted measurement data. The window was resized and the successful run is separately recorded. The actual nominal frame-limit option is **260**, not an uncapped-throughput claim.

The fixed receiver is 81 white-concrete cells at X432/Y157..165/Z-387..-379; the target is 49 cells at X426/Y158..164/Z-386..-380, with two fixed sea-lantern upper corners. All 130 cells must be exact AIR before each placement, including the absent wall in the open control. Each variant cleans only its own expected states, preserves unexpected replacements and records an ownership journal. An independent [saved Anvil audit](before/persisted-air-post-stop.json) checks these 130 plus the previous 260 near/far fixture cells: **390 exact AIR**, no pending journal. This reads actual saved block palettes, not just the runtime cleanup flag.

The [new 0.3.2 air controls](after/RESULTS.md) repeat exactly those geometry, time, actor, resolution and eye/camera contracts. All six old/new panel images were visually reviewed by the root and another Codex agent. Both versions' closed walls hide the magenta target and its fixed light markers, and the open controls reveal it. In 0.3.2 the conspicuous pale, horizon-aligned wash on the backlit wall and open panel is reduced/absent; the shaded wall remains dark blue-gray, the sunlit wall remains cream-white, and terrain colours are less gray-veiled. This is not a global darkening. Sequential clouds/exposure may differ, so images support visual/control validation, not pixel-exact causal attribution.

The [ten compatibility scenes](compatibility/RESULTS.md) cover ocean/coast/day/dusk/night/rain, underwater, cave water, glass, Nether and End. All run with the frozen new ZIP, no Iris fallback, correct dimensions and actual locked cameras. Each compatibility scene is only **5 s warmup + 5 s measurement**; air controls use **10 + 10 s**. CSV nanosecond intervals were independently recomputed: 7,665 before, 7,548 after, and 13,759 compatibility intervals. The Overworld compatibility means are **157.6–212.2 FPS**, worst interval **10.251026 ms**; no interval in these short runs exceeded 16.667 ms. This is not a general floor guarantee. Nominal cap 260 is recorded; Nether/End report higher render-loop rates, so their numbers are not presented as cap-enforced throughput or used to claim general speed improvement.

Root visually reviewed every compatibility scene after checking PNG integrity. Water reflections, underwater attenuation, dark cave/night appearances and glass remain functional; Nether/End contain no Earth sky. Existing strong cyan shallow water, screen-space refraction boundaries, procedural cloud appearance and simplified horizon/lighting remain quality limitations, not a claim of photorealism.

The [persisted AIR audit](persisted-air-post-stop.json) again verifies all **390 cells are exact AIR**, no pending ownership journal, after both main new-version runs and test-client stop. The later [export-check post-stop audit](export-check/persisted-air-post-stop.json) independently repeats that result after the final instrumented run. The finishers returned to Overworld before marking each run complete.

### Asynchronous screenshot export repair

The initial benchmark exporter used file existence/nonzero size as a readiness signal. One copied Nether PNG was therefore truncated at **2,097,152 bytes**, although Minecraft's original native capture finished at **4,358,271 bytes**. Metadata and CSV audits alone did not detect this. Root's actual image decode rejected it. The incomplete export was preserved under the gitignored `build/rejected-v0.3.2-nether-partial.png` (SHA `f413c687cfe1ee9476acb7c13875fe942dc31b3793e0b1b42984133784e10bcf`).

The completed original **same capture**, not a different rendered scene, was decoded successfully and copied into the report and local run export. Original native image was preserved; recovered PNG SHA is `1a6d52b7e9d8f5b0024d2f82fd8fbe8026e4964b595504348fd18938a2203931`. Raw timings, metadata, camera and render configuration were not altered. After recovery **all 16 old/new/compatibility PNGs fully decode with ffmpeg**, with zero decoder diagnostics. Metadata-only audit passes must not be mistaken for image-integrity passes.

The producer now uses a per-capture thread-visible completion token and waits for Minecraft's verified `screenshot.success` callback after its native file writer returns. Failure, unknown callback and 15-second timeout reject; a delayed old callback cannot authorize the next capture. The report independently checks PNG dimensions, chunk order, every CRC, IEND, exact bounded zlib scanlines and filter markers (16 MiB encoded bound, no unbounded decompression). Four Java regression runners and 17 Python tests pass, including actual report rejection of an incomplete capture.

A fresh [Nether export check](export-check/RESULTS.md) actually ran the corrected producer on Minecraft, same frozen shader ZIP and dedicated world, 5+5 seconds. It completed without recovery: exported/native PNG hashes match exactly, `a490f5a6cde85fd0cab24fedfdcbfdec4f8fc94436ac63599159e94898239fea`, and the strict report validator passes. This validates the callback reflection and producer in the actual runtime, not only a CPU mock. Shader sources were not changed during the export repair.

The first 16 captures used benchmark JAR SHA `5af50d3265c91c5b72573bafa191f51409325c74e95aa01d8540ed56c7edfbac`; the corrected producer/export check uses SHA `683f5156f024f0fbf8eec4dac015fcb6a1525b89d6702bc8174cc2b2f4a3cc80`. Both have instrumentation version 0.3.2; their identities are distinguished here rather than claiming the earlier runtime ran the later source. A final independent read-only audit accepted all **17** benchmark PNGs and recomputed all **32,333** CSV intervals; it also re-read the saved eight Anvil chunks and confirmed all 390 reserved cells are AIR. The original partial PNG still correctly rejects.

### Test-client shutdown limitation

After completed runs and verified cleanup, UI Save-and-Quit stalled after test-player disconnection in each of the three isolated offline test-client sessions (old baseline, new-version main runs, and corrected export check), as in the earlier instrumentation run. The original user's client had saved all dimensions and exited normally before testing. For each stuck **offline test client only**, its PID and Lab working directory were rechecked, the saved 390-cell AIR audit passed, and that specific Java process was stopped with TERM, followed by its own launcher. The post-stop audits again passed. No user-world process was force-stopped, and no fixture or world was deleted. A completed scene capture/cleanup or repaired screenshot export is not a claim that instrumented-client shutdown has been repaired.

## Release and normal-world restoration

The built and installed `Aqualumen-0.3.2.zip` both hash to **`7b5bdfb78e79b3214ca2a1fca77657c88680dbf46ef1b875dd95c0eeb652a9c2`**. The ZIP was rebuilt reproducibly before Minecraft validation and remained frozen throughout all new-version runs. The physics 0.2.0 JAR is unchanged, SHA `1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e`. The historical 0.3.1 ZIP and both benchmark builds are preserved.

All benchmark JARs are disabled, and the opt-in marker is absent (preserved under a release-disabled filename). Original `options.txt` was restored **byte-for-byte**, including 1600x900, max FPS 120, pause-on-focus-loss, render distance 12 and simulation distance 6. Instance window settings are restored to 1600x900; Java/memory settings are unchanged. Iris selects the new ZIP. The ordinary account `kusutohu1128` was launched into its existing `新規ワールド`, with no offline-account override or benchmark commands.

The [filtered runtime log](restoration/runtime.txt) confirms the normal account, 17 loaded mods, new shader selection and Overworld pipeline without a recorded error or exception. The [actual normal-world debug screenshot](restoration/normal-world-debug.png) confirms NVIDIA RTX 3080 Ti, Java 21.0.7, 1600x900, cap 120, `BALANCED`, Iris 1.8.8 and the new ZIP, at the user's saved position `(124.1105,70,38.6510)`. This is an ordinary night-time view, not another benchmark or a replay of the supplied daylight screenshot. Debug display was then turned off and the game left paused for the user.

## Interpretation and remaining limits

The supplied image has the sun above the crest: air in front of a shaded wall can genuinely receive sunlight. This fix must not eliminate all fog or indirect light on opaque geometry. It removes the unrelated whole-sky contribution and unsupported out-of-coverage direct light, rather than requiring every shadow to be black.

The local ambient closure, weather density multiplier and camera-position solar cache are approximations, not calibrated atmospheric measurements. Ten midpoint shadow samples may miss thin blockers; there is no complete world-space ray tracer or GI. The inherited `depth<0.999999` foreground classification is unchanged. Very distant geometry and transparent-layer optical paths still have limitations. Surface lighting itself is not redesigned by this update.

The user had moved away from the screenshot location before testing. Their normal world, account and saved position were preserved; no benchmark teleport or time commands were issued there. Isolated controlled scenes are a reproduction of the mechanism, not a pixel-exact comparison of that original hillside. FPS is an observation, not a 60 FPS guarantee.

## References and review provenance

The finite-segment formulation follows the [volume transport equation](https://pbr-book.org/4ed/Light_Transport_II_Volume_Rendering/The_Equation_of_Transfer), using original local GLSL rather than a copied renderer. The sky coefficient convention is shared with our existing [Bruneton-inspired approximate atmosphere](https://ebruneton.github.io/precomputed_atmospheric_scattering/). Camera semantics follow [Iris coordinate spaces](https://shaders.properties/current/how-to/coordinate_spaces/).

This update's static design review and implementation are by Codex agents. No fresh Claude Opus/Sonnet response or independent Claude game validation is claimed; earlier actual Claude contributions remain attributed in their original records.
