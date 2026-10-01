# Aqualumen 0.3.3 — underwater directional sky

## Cause and requested appearance

The user's [supplied image](user-scene/user-supplied.png) shows a four-sided cloud-map boundary and two pale sun-like images inside an otherwise curved underwater window. That inner boundary is a rendering error, not the natural Snell-window/total-internal-reflection rim.

The old production water shader projected a refracted ray toward a finite 48-metre point, sampled the pre-rendered camera image when it stayed in the viewport, and returned the original unrefracted UV on a miss. The preimage of that rectangular viewport is a distorted quadrilateral within the physical circular transmission cone. Switching between those two sky mappings explains the cloud discontinuity and duplicated disk.

The fix retains the chosen water/air indices **1.333 -> 1.0**, exact Fresnel and total internal reflection. With a flat interface the angular window diameter is approximately **97.21 degrees**, derived from `2*asin(1/1.333)`. Strong compression toward its rim is physically expected; eliminating the whole circular effect is not the goal. See the [reflection/refraction formulation](https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission).

## Test-first implementation

An actual production `gbuffers_water.vsh/fsh` regression failed on the RTX 3080 Ti before shader edits. Its only shader configuration override is the public `WAVE_HEIGHT=0` setting, allowing a flat interface. Input depth, directional sky, direct/diffuse illumination and camera geometry are controlled, and no sampled texture is attached as the output target.

Two transmitting rays are tested: **19.9513 degrees**, whose old projected UV is **0.650517**, and **43.0286 degrees**, whose projected UV is **1.13165**, outside the viewport. Changing only the camera-sky texture red -> green changes the old output by **0.969167 RGB**, although each ray's directional sky is fixed. After the fix the difference is **0** and both rays receive their distinct directional-LUT colours, attenuated by the correct Fresnel transmission. [RED](native/underwater-sky-red.txt) / [first GREEN](native/underwater-sky-green.txt).

The refraction tracer now reports three receiver classes:

| Class | Water-underneath transmission source |
|---|---|
| Converged visible opaque receiver | Existing refracted `colortex4` geometry |
| Observed screen sky depth | Sky LUT in the transmitted world direction, plus analytic Sun/Moon |
| Unknown/miss | Existing cave/environment closure blended toward directional sky by sky exposure |

Unknown depth is not silently treated as a successful original-UV geometry hit or proof of open sky. Above-water tracing/fallback policy, absorption/scattering coefficients, waves, contact physics and the 0.3.2 finite-air model are retained.

The atmosphere/cloud LUT does not contain the analytic Sun/Moon disks. A shared `environmentSkyRadiance` helper includes both and uses the same expression as the prior deferred sky. Water evaluates it before varying trace/Fresnel branches, with a safe substitute only for the otherwise zero TIR refraction vector. The final pure-reflection result does not use that substituted sky.

A separate incremental regression exposed the old `normalize(-worldPosition)` assumption. Applying a consistent coordinate translation `(0.4,0.3,-0.2)` to geometry, view/inverse-view, camera and shadows preserves the physical scene, but previously changed RGB by **0.587374**. The eye is now `relativeWorld(vec3(0))`, and the view vector is `normalize(eye-worldPosition)`: the same test gives **0**. This is a general inverse-modelview correction, **not a fixed 1.62-metre adjustment**, nor a measurement of the actual user's head-bob amplitude. [Eye RED](native/underwater-eye-red.txt) / [eye GREEN](native/underwater-eye-green.txt).

## Native verification

[Final targeted checks](native/underwater-sky-final.txt) and [full check](native/full-check.txt) passed on `NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2`, OpenGL `4.6.0 NVIDIA 580.173.02`. All 11 graphics pairs and three compute shaders compile/link; prior aerial haze, cloud MRT, sky-LUT, water/refraction/extinction, tone mapping and persistent wave-field tests pass.

New positive/negative controls also establish:

- Independent Fresnel reference, maximum error **6.60206e-08**; a roughly 50-degree TIR ray does not transmit sky.
- Actual production-main opaque receivers still obtain refracted scene colour.
- Unknown closed-cave rays stay dark, maximum RGB **0.000117475** under the controlled lighting fixture.
- Analytic Sun and Moon remain visible on a bare-black sky LUT, but neither leaks through the TIR control.
- Consistently translated eye/scene coordinates preserve output.
- The production tracer retains the former above-water fallback UV/path, commits converged opaque distance, and distinguishes sky from a miss.

These are controlled optical/source regressions, not measurements of Minecraft FPS or full-world occlusion. GPU harness work finished before isolated timed Minecraft scenes.

## Actual user-scene comparison

The root captured [before](user-scene/before.png) and [after](user-scene/after.png) in the user's existing `新規ワールド`, at **XYZ `(367.606,60.16977,116.682)`**, yaw **172.2**, pitch **-67.5**. [Before debug](user-scene/before-debug.png), [after debug](user-scene/after-debug.png) and [filtered runtime log](user-scene/runtime.txt) confirm the same pose, 1600x900, BALANCED, NVIDIA renderer and selected old/new packs. No teleport, time command, benchmark request or terrain edit was issued in this ordinary world; only the shader was reloaded.

Both root and another Codex agent independently inspected the images. The quadrilateral inset and discontinuous/repeated cloud mapping are absent after the fix, and only one pale disk-like image is visible. The curved transmission window remains, its outside stays dark, and sky compression near the critical rim remains. Clouds and natural time evolved between captures, so this is an actual matched-pose visual check, not pixel-exact causal or calibrated radiometric comparison. The user's world was then [saved normally in all dimensions](user-scene/saved-world.txt) before isolated validation.

## Isolated runtime validation

All three isolated runs completed and passed the strict report validator:

- [Old 0.3.2 upward views](before/RESULTS.md): near surface, deep and tilted upward.
- [New 0.3.3 upward views](after/RESULTS.md): identical three planned poses, mean **248.3 / 240.8 / 249.7 FPS**, worst **6.286 / 6.962 / 7.211 ms**.
- [New compatibility views](compatibility/RESULTS.md): ocean, coast, dusk, night, rain, underwater, cave water, layered glass, Nether and End; worst measured interval **10.418 ms**, in layered glass.

The disposable `AqualumenNaturalV2` save has UUID `b22dbccb-2970-41e6-847f-f183b1ec923d` and seed 308060. These runs used the same offline TEST client, NVIDIA renderer, 2560x1440 framebuffer, BALANCED, 12/6 chunks, VSync off and nominal frame-limit setting 260. Each scene had **5 seconds warmup + 5 seconds measurement**. There was no simultaneous native GPU test. The cap is recorded as a setting, not asserted as an enforced limit in the Nether/End measurements. These short warmed-view observations are not a universal FPS floor or quality score.

The three upward scenes use `(448.5, -383.5)` X/Z, yaw -45, and pitch -90 / -90 / -65. The near/tilted player Y is 60.7689 and deep Y is 58.0189. Recorded fluid surface height is 62.88888931274414; actual near eye depth is approximately 0.4998893 m. The instrument checks the real eye position, rendered first-person camera, entity submersion, WATER camera medium, fixed daytime 6000 and clear weather. Upward scenes place no terrain. Authorization requires the exact disposable UUID/seed/generator, one identified local player and no LAN publication. The pure Java planner and Python control/report tests passed, including rejection of invalid poses and missing submersion evidence.

Root and an independent Codex auditor inspected the captures: the inner quadrilateral disappears in **all three** new upward views, while the curved Snell/TIR boundary and deeper-water attenuation remain. Compatibility scenes retain functioning water, cave darkness, glass and distinct Nether/End environments without an Earth sky. Strong cyan shallows and sharp screen-space geometry/refraction boundaries are existing limits, not claimed fixed. The [independent audit](INDEPENDENT-AUDIT.md) rechecked **16 PNGs and 21,132 raw intervals** against recorded identities, poses, durations and metrics. Every captured PNG passed complete CRC/zlib/dimension validation; all six upward exported/native PNG pairs matched SHA-256.

All run completion records report `fixture_cleanup_complete=true`. Bounded read-only saved-Anvil checks [before shutdown](persisted-air-pre-stop.json) and [after test-process exit](persisted-air-post-stop.json) independently found **390 exact AIR cells**, no pending ownership journal and `cleanup_pass=true`. Region bytes changed during the lifecycle, so cleanup is established by decoded saved block states, not a claim that the whole region stayed byte-identical.

The offline TEST client again stalled after its Save-and-Quit disconnection, a known instrumented lifecycle limitation also observed in 0.3.2. After completed runs, pause/save evidence and cleanup validation, only that identified test Java process and its own launcher were terminated. Its save was audited again after Java exited. This release does **not** claim that instrumented shutdown is repaired. The ordinary user's client/world had already saved and exited normally before these tests. The offline profile's expected authentication-property fetch error is separate from shader health; there was no Iris shader fallback.

## Release and ordinary-play restoration

The final reproducible ZIP is installed in Aqualumen Lab, selected and active without fallback:

| Artifact | SHA-256 |
|---|---|
| Final installed/built 0.3.3 ZIP | `ff81efa32c96f3b1c2c76c1c55fe6e32ed29f1344e67a239afeeccca980583e5` |
| Preserved installed 0.3.2 ZIP | `7b5bdfb78e79b3214ca2a1fca77657c88680dbf46ef1b875dd95c0eeb652a9c2` |
| Unchanged physics 0.2.0 JAR | `1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e` |
| Test-only benchmark 0.3.3 JAR | `78d3b56877c0d3f9a8a9133aed8865ee7c42498bd7ed19a7d1a43cefd71f9c10` |

The benchmark JAR and enabling marker were recoverably renamed to disabled files before normal launch. No active benchmark JAR or marker remains. The original `options.txt` was restored **byte for byte**, including cap 120, pause-on-lost-focus true, and 1600x900 overrides; launcher window dimensions were restored too. Java/ZGC/heap settings and other instances were retained.

The normal `kusutohu1128` account was then launched into its existing `新規ワールド`, with no offline identity override or automation. The restored client selects 0.3.3 and initializes the unchanged physics bridge. Its debug capture confirms the original XYZ/yaw/pitch, 1600x900 and unchanged BALANCED defaults. It is left paused, debug display off; Escape resumes ordinary play. See the [restored runtime](user-scene/restored-runtime.txt), [restored debug pose](user-scene/restored-debug.png), [paused handoff](user-scene/restored-paused.png) and [final evidence checks](native/evidence-audit.txt). No ordinary-world teleport/time command or terrain edit was used.

## Remaining limits and provenance

Visible ground is still screen-space refraction, not world-space ray tracing. Offscreen/hidden banks or cave ceilings can be missed; an observed sky pixel does not prove a world ray is unobstructed. The inherited far-depth threshold and 48-metre geometry search limit remain. The sky-exposure closure, water/environment colour and TIR reflection fallback are approximations, and ideal disk antialiasing exactly at the critical boundary is not guaranteed. This release does not claim all water artefacts, fluid dynamics or photorealism are solved.

Implementation, static review and native/runtime checks in this update are by Codex. [Static review](../../docs/reviews/codex-v0.3.3-underwater-review.md) identifies its exact source snapshot; it is not a fresh Claude Opus/Sonnet review. Earlier genuine Claude contributions remain attributed in their original records.
