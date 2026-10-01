# Independent v0.4.0 real-image visual audit

Reviewed 2026-10-02. **The current coast/river appearance does not yet meet the convincing-real-shallow-water goal.** The production fixes have useful bounded numerical evidence, but the real captures still show strongly cyan/mint shallow receivers and sharp, serrated dark/clear water bands. These images do not establish that all shoreline artifacts disappeared, or a clear photorealistic improvement over 0.3.3.

This reviewer read the exported metadata/raw CSVs, reran the existing strict report loader without writing its output, hashed the artifacts/source, and visually inspected all 20 stills. No GPU harness, game/control requests, lifecycle operations, configuration changes or shader edits were performed. The only review edit is this document.

## Provenance and comparison limits

| Capture | Run ID | Active ZIP SHA-256 | Scenes |
|---|---|---|---:|
| Before | `water-v0.4-before-v0.3.3` | `ff81efa32c96f3b1c2c76c1c55fe6e32ed29f1344e67a239afeeccca980583e5` | 4 |
| After | `water-v0.4-after` | `5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069` | 16 |

Evidence is under [`before`](../../reports/2026-10-02-v0.4.0/before/RESULTS.md) and [`after`](../../reports/2026-10-02-v0.4.0/after/RESULTS.md). Both actual `dist/` ZIP hashes equal the corresponding run/scene metadata. The six production source hashes below also byte-match their entries in the after ZIP.

Both runs identify the same isolated `Aqualumen Lab/AqualumenNaturalV2`, exact world UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`, seed `308060`, vanilla noise/Overworld generator, local player and integrated-server/no-LAN guards. They record Minecraft 1.21.1, Iris 1.8.8, Sodium 0.6.9, benchmark 0.3.3, physics 0.2.0, Java 21.0.7 and the actual NVIDIA RTX 3080 Ti / NVIDIA 580.173.02 renderer. Window and framebuffer are both 2560×1440, render/simulation distances 12/6, VSync false, **recorded frame-limit setting 260**, default pack options and ZGC with 2/6 GiB initial/max heap. Effective Minecraft/Iris clouds are OFF; that does not disable the shader's procedural clouds.

The four A/B pairs have exactly equal recorded actual player/camera positions and rotations:

| Scene | Player XYZ | Rendered camera XYZ | Yaw / pitch |
|---|---|---|---|
| coast-day | `(-191.5,64.1,320.5)` | `(-191.5,65.71999988555908,320.5)` | `0 / 9` |
| river-day | `(-63.5,64.1,-63.5)` | `(-63.5,65.71999988555908,-63.5)` | `-45 / 9` |
| ocean-day | `(448.5,64.1,-383.5)` | `(448.5,65.71999988555908,-383.5)` | `-45 / 9` |
| underwater-up-near | `(448.5,60.769,-383.5)` | `(448.5,62.38899988555908,-383.5)` | `-45 / -90` |

The upward pair additionally passes actual first-person/eye-position, touching/submerged-water and rendered-camera WATER validation. Measured surface Y is `62.88888931274414`; actual eye depth is `0.4998893079757707` m and camera-to-eye Y mismatch is about `1.19e-7` m. Both client/server times are 6000. The deep/tilted candidate scenes pass their existing exact pose/submersion validators too.

These are matched-pose observations, **not fixed-phase pixel controls**: shader wave/cloud time continued, entities moved, and the runs were sequential. A changed dark stripe, cloud outline or animal position alone is not a shader regression/improvement. There are no before captures here for the other twelve after scenes.

Additional timing-condition caveat: the ocean-day/upward-near before captures record `window_focused=true`, while their after captures record `false`. That field is a capture-time observation, not a full focus-history trace; the two timing workloads therefore are not strict matched-condition performance controls. The moving-view after capture also records actual yaw `14.979683` versus expected `15.061745` degrees, a difference of about `0.082062` degrees. Its actual camera/player rotation agrees; this continuously rotating scene is not an exact static-yaw pair.

## What the real stills show

| View | Independent observation | Conclusion |
|---|---|---|
| Coast A/B | Both retain a large saturated cyan shallow-bottom area, pale mint/yellow sand steps, broad jagged dark/clear patches and hard shore transitions. The detailed wave/patch outline changes, but there is no convincing removal of those dominant features. | Shallow-water visual goal remains unmet; no claim that the synthetic continuity repair solved all real banks. |
| River A/B | Both retain pale mint/cyan foreground water against dark gray-blue bands and stretched vegetation reflections. Distinct coarse bottom/wave transitions remain. | No clear general appearance improvement established by this pair. |
| Open ocean A/B | Gray-blue cloud reflections and fine wave bands remain coherent; no missing-water surface, major overbright cyan field or camera-image rectangle is introduced. A narrow beige horizon band and stylized low-contrast sea/sky transition remain. | Compatibility preserved in this view; phase changes do not prove a beauty improvement. |
| Underwater-up-near A/B | Both show a round, Snell-window-like directional sky opening with dark blue surroundings, rather than a rectangular camera-image fallback. | The 0.3.3 directional-sky correction is visually retained at this pose. |
| Underwater / up-deep / up-tilt | The forward underwater view is dark blue/hazy with faint bottom and kelp. Deep/tilted upward views retain curved sky/TIR boundaries and no viewport rectangle. Vanilla square ambient particles are visible. | No obvious upward-sky regression seen; water visibility and TIR correctness are not calibrated against real measurements by these images. |
| Dusk / night / rain | Dusk gives a warm orange horizon/water reflection; night is dim blue rather than luminous shallow cyan; rain is visibly overcast with dense vanilla rain streaks. | Distinct lighting/weather behavior is present. Dusk does not show the solar disk here, and there is no matched before for a sunlight-quality claim. |
| Moving-view still | Open-water reflections remain, but a cyan bottom patch and sharp step/band transitions are visible on the right. | Another observable shallow-water limitation, not evidence of temporal smoothness from one frame. |
| Cave-water | Muted gray-blue water occupies narrow lush-cave channels; there is no obvious bright daytime sky leaking into the shown sheltered water. White-gray edges around plants/water remain. | Useful cave compatibility observation, not all-cave coverage or proof of realistic cave foam/illumination. |
| Glass-layers | All three temporary glass slabs are visibly transparent with their blue borders; the ocean/clouds remain visible. | No obvious depth/fallback failure here; not a physical glass-energy/refraction validation. |
| Nether / End | Dimension-appropriate red/brown lava terrain and purple/dark End sky remain; no Earth clouds/day sky are introduced. | Non-Earth fallback compatibility retained, not Earth-atmosphere physical validation. |
| Boat-contact | The mounted boat and water render without a catastrophic missing-water/fallback defect. Instrumentation measured one contact and maximum force `0.2208`. | Real bridge input exercised. The driver was scripted server-command translation at 6 m/s/20 Hz, not vanilla rowing; one still does not validate wake dynamics. |

No new obvious rectangular-sky or dimension-fallback regression was found in the reviewed stills. That limited compatibility result must not be expanded into "all rendering regressions absent."

## Numerical repair versus remaining realism gaps

The separate production-main native continuity test preserves the original tiny bottom-depth bracket `2.59984375→2.5998828125` m: RED had a finite blue/RGB jump `0.066329`; GREEN reduces it to `5.70714e-6`. Direct-Sun attribution/zero-energy and paired-depth controls also pass in the separately recorded native evidence. This supports the diagnosed smooth-receiver handoff and source-energy fixes, not arbitrary shoreline continuity or visual realism. The native test did not prove a late-iteration bank crossing, and a still cannot attribute a jagged patch to a particular trace exit.

The next quality priorities remain falsifiable rather than a global tint adjustment:

1. Separate the large cyan receiver's bottom illumination, view-path extinction and in-scattering. The receiver is still ordinary terrain-lit before the water view leg; the new direct-Sun isolation prevents focusing ambient/block light, but does not add a fully reconstructed surface-to-bottom illumination path. Correct provenance need not make that shallow receiver look physically convincing.
2. Distinguish remaining reflection/normal/proxy handoffs from actual bottom edges using production output controls at these exact coast/river poses and fixed phase. The observed serrated bands are not labelled hit/miss diagnostics; do not assign a cause by appearance or relax foreground-bank rejection to blur them away.
3. Check local shore amplitude/foam against surface geometry and camera motion. Screen-ray receiver height is still an approximation to bathymetry; natural stepped blocks can have genuinely sharp edges, but the current broad flat-color and dark-band pattern remains a visual quality gap.

See the separate [source/probe review](v0.4.0-shore-diagnosis.md) for current-policy audits and explicit native test limits. No claim of photorealism or complete water/light transport is supported here.

## Integrity, timings and cleanup boundary

Independent read-only `tools/report.py::load_run` recalculation passes all **20 scene PNGs and 18,506 positive raw render-loop intervals** (before 3,889; after 14,617), including bounded PNG chunk CRC/order/zlib/full-scanline validation, scene dimensions, active pack SHA, actual camera identity/angles and upward submersion metadata. Both runs have complete markers and no abort record. Their runtime completion records say `fixture_cleanup_complete: true`; independent persisted post-stop terrain verification is not part of this still-image audit.

Both requested only 5 s warmup + 5 s sample per scene. Observed paired means were coast `172.22→159.58`, river `176.52→160.86`, ocean `173.62→136.08`, upward-near `255.69→192.11` FPS. These are wall-clock render intervals, not GPU-only throughput, controlled repeat averages or a causal performance result. The candidate's worst intervals include `17.088164` ms at dusk and `21.775271` ms at night. There is no 60 FPS floor guarantee, and that former budget is not the user's current visual-quality release gate.

## Temporal evidence status

The first 1440p X11 captures are complete but **not accepted as full-frame quality evidence**. The provided decoded coast frame has a large black right/bottom region from offscreen-window capture, not a demonstrated shader output defect. The visible portion confirms that cyan/serrated coast patterns persist, but missing image coverage prevents a whole-frame temporal acceptance.

| Retained diagnostic attempt | Probe result | SHA-256 |
|---|---|---|
| `build/quality-v0.4.0/coast-animation.mp4` | H.264, 2560×1440, 20 s, 1,200 frames, encoded average 60 fps; clipped | `1df2eac5ebae7e042d2fad3327eb91aaf400e9b3cc8d913d02299c4f759463fb` |
| `build/quality-v0.4.0/moving-view.mp4` | H.264, 2560×1440, 24 s, 645 frames, encoded average 26.875 fps; root-reported clipping | `f7f9c918440109c86e69b5e217d06910d2082322df0df722b5d2dd445f016239` |
| `build/quality-v0.4.0/coast-t08.png` | Independently viewed clipped decoded frame | `199021953d4d7cc0722330d9310fe0bc6172e028794103d59c1dc518b103e50d` |

Encoded frame rate is not the Minecraft rendering rate or evidence of no duplicate/stalled frames. Replacement full-window captures were pending at this initial review; their subsequent limited review is recorded below. They must remain separate from the 1440p still/timing runs.

## Audited source SHA-256

| After production source | SHA-256 |
|---|---|
| `shaders/gbuffers_water.fsh` | `ae9c2989deb53b27129b65367c1cf4969e4d3b9a314b3838fca483c8327e3c04` |
| `shaders/composite.fsh` | `618ef89b663783b3a97b924f21a9188dbd1883ee83d71ab0ca3c9a64d8601e18` |
| `shaders/deferred.fsh` | `e6f799d997e7e5c08d07c54cb954fd1c6e5d86bc93471eb6ce09361fe3b2ada9` |
| `shaders/lib/terrain.fsh.glsl` | `2e2073cfab36190d31f36af79e17a4e24208bb93f4189204c9442db440a0add9` |
| `shaders/lib/lighting.glsl` | `16cf5a6c9b78b70b7cef735a58628742dffe8249fdba8443ede4a2a088ab2e34` |
| `shaders/prepare.fsh` | `a4919f0cf43f77a736b3b92b386c4b7625fc06f1df5d9e07f5160cfc29fb084e` |

## Visually reviewed still SHA-256

Paths are relative to `reports/2026-10-02-v0.4.0/`. Full hashes identify the unchanged reviewed originals, not crops or edited illustrations.

| PNG | SHA-256 |
|---|---|
| `before/coast-day.png` | `39f46241a561cac8a9781981ac85a7d000e49f9deed645c242da7889e69b2939` |
| `before/river-day.png` | `4e3031668118d5b46565db6cf5b117e9c5ec8825ca2ba7e1ee6a154408132056` |
| `before/ocean-day.png` | `45ddf484bef9592f3b0f8b340e15364c2d81dce8826f764d89d9643986e848ed` |
| `before/underwater-up-near.png` | `338e092ffef682a20e5ce6be2247579649e4939edf6d96ecb1ea8be995deb8e7` |
| `after/coast-day.png` | `5dcf855bdcbd13b1764a59053b5e02d6bb96e1c8365cd71468203cd241a2332f` |
| `after/river-day.png` | `782a6df4b39c7fb6b772a3158b22b7da8c45172e6f03eccca9391c1280c53ada` |
| `after/ocean-day.png` | `5923f75c93530dff275cf444784d7c6d51b0f0503acfec06913262ae0a0d497d` |
| `after/ocean-dusk.png` | `36b572673c6038952ac097ed3e6eb8bbdb1704d133cda6bbd15fc2c7d994f85a` |
| `after/ocean-night.png` | `d14ab08a8d2b914a2dbe0f8ee7b934972d2bf5e21fe92b2878ddb17bcf3125db` |
| `after/ocean-rain.png` | `eeec9871f01089b2311a7d70087aa6f25c29ceeb25bf042dcea0d9aeb21d4afa` |
| `after/underwater.png` | `0f6f8d78f22c88ec7f587bcfaa79c123f14237724d7f0fc8968e671a2fba498e` |
| `after/underwater-up-near.png` | `20aa1380cebd095e09f6cd06b4af88122ece8b29276f7b9ed240fd8ed2b06b19` |
| `after/underwater-up-deep.png` | `c200d25b2dc4fff82c386748570def1877a750160318f82f73c9eff3aa913c9e` |
| `after/underwater-up-tilt.png` | `b99d29c3321b1c61a8f2680e8066460e7e9a967f6da2210b946e3b6623fb458a` |
| `after/moving-view.png` | `1dc33269f3b0724781e119ad122ff9876531820bf129769d5fea9e44a8e1806f` |
| `after/boat-contact.png` | `c7ecb062f0205e019377cf5b265ec4bb1cefd5d407800f75035de1660f03d7b8` |
| `after/cave-water.png` | `7dcac37297761b2cd8f9be853347011edc87f9f9c17a2c078ca34b7f00d9d17a` |
| `after/glass-layers.png` | `335a8cb4bae21ad6242ad86640a6e6ac3003b8e574bed85e113b94af3b5631ad` |
| `after/nether-view.png` | `1fa48b355ab1b5500f05f729570f746171b136e55463922d858b5257ab9eeb36` |
| `after/end-view.png` | `563a18d039981c752bfb9e13890f60dbe94274226a02eaca95d549eb14a7d6cd` |

## Addendum: completed full-window temporal sampling

The root reported the replacement sequence terminal/complete at `2026-10-01T19:53:28.637884630Z`; the reviewer waited until recording ended before decoding. `reports/2026-10-02-v0.4.0/temporal-run` identifies run `water-v0.4-full-motion`, the unchanged 0.4.0 ZIP SHA/world UUID/seed above, **1600×900 window and framebuffer**, five-second warmup and thirty-second samples, and complete cleanup. Capture-start status snapshots associate the three clips with each scene's sampling state. This is a different resolution/load from the 1440p A/B, not a substitute timing baseline.

All three completed H.264 clips probe as 1600×900, 20.000 s, 1,200 encoded frames, encoded average 60 fps. CPU-only full decodes returned exit 0 with no reported decoder errors. **Visual review sampled five frames per clip** at 0.5, 9.9, 10.0, 10.1 and 19.0 s; it did not watch every moment or certify every transition. The root supplied 0.5/10/19 s frames, and the reviewer extracted only the six additional 9.9/10.1 s frames with `ffmpeg -n`, after recording ended, without overwriting originals. All fifteen reviewed decoded PNGs pass the bounded integrity checker.

| Clip under `build/quality-v0.4.0/` | SHA-256 | Sampled-frame observation |
|---|---|---|
| `coast-day-full-motion.mp4` | `f32bb24a51e1623c4770396d108151790230275b727366c4fe57b250506c90e9` | Full-frame coverage, without the old black clipping. Large cyan region and serrated dark/clear bands persist at all five samples. Shapes change with waves; this is not shoreline visual acceptance. |
| `moving-view-full-motion.mp4` | `3b283922881ce48e42ffb77010c7d9d8ec7387735d616f6f74a6d4d6f564447b` | Viewpoint clearly changes; open-water reflections remain and cyan/blue stepped bottom patches enter the view. No full-screen missing-water/fallback rectangle in the selected frames. These samples do not prove absence of popping during the pan. |
| `boat-contact-full-motion.mp4` | `62ab219ae7125023eafb39d79f4050e9fe751fe9a884159514ce5568ab216dc9` | Boat geometry changes markedly relative to the camera around 9.9/10/10.1 s, so smooth boat-relative motion is not established. The bow/hull obstructs foreground water and the wake behind the boat is mostly outside the view. A saving-world toast appears at 0.5 s. No calibrated wake-quality conclusion is supported. |

The boat uses the existing 6 m/s, 20 Hz **server-command teleport driver**, not rowing. Its contact samples are nonvacuous (one contact, maximum force `8.0`), but the clip's unusual boat-relative position does not by itself establish whether interpolation, commands or rendering caused it. The coast sample also records up to two contacts/force `2.2749`; it is a stationary camera, **not a contact-free wind-only control**. These must not be conflated with the original 1440p coast's zero contacts or boat force `0.2208`.

Independent bounded PNG checks and raw CSV recomputation pass the four temporal-run scenes (including the non-video upward-near guard scene), totaling **28,561 intervals**: coast 6,397; moving 6,646; boat 6,584; upward-near 8,934. Actual camera identity, pack/world/resolution and complete marker agree. `load_run` intentionally requires 2560×1440, so this is an explicit read-only 1600×900 metadata/CSV/PNG audit, **not** a claimed pass of that unchanged 1440p report boundary. Capture-time focus is true in these four records. Their means/worst are respectively `213.246/11.492394`, `221.546/13.046871`, `219.467/11.812296`, `297.804/7.208335` FPS/ms, with capture load included; no performance guarantee follows.

This closes the earlier **coverage** deficiency, not the water-realism or whole-clip smoothness questions. There is still no matched old/new temporal control, causal artifact attribution or accepted physical wake demonstration.

### Remaining jagged-shore hypotheses and one-variable controls

These ranked candidates came from read-only production-source inspection using the diagnosis skill's falsifiable-control approach. No new shader probe was run for them. The real repeated coast captures are the appearance repro; the existing smooth-floor native test is not a failing causal seam for every jagged natural bank.

1. **Optical normal versus coarse geometric surface.** Vertex displacement uses long-wave detail (`gbuffers_water.vsh:26`, `waves.glsl:41,65`), while fragment normals retain filtered short-wave slopes and drive point Fresnel/refraction/reflection (`gbuffers_water.fsh:181–207,261–272`). At fixed phase/geometry, replacing only the optical normal with the geometric normal should remove large dark/clear bands if unresolved facet optics dominate. Retain all other components, then isolate them separately; roughened sky/Sun lobes do not integrate the point Fresnel/ray visibility.
2. **View-ray depth modulates normals differently from geometry.** Original-screen receiver height controls the wave slope taper (`gbuffers_water.fsh:168–181`, `waves.glsl:56–59`), while vertices use depth 64. Hold only the fragment wave-depth input at 64, preserving refraction/foam depths: seams that disappear implicate that coupling. Broad artifacts where depth exceeds 0.8 m would rule out the taper alone. Foam-off is a separate control for white shore edging, not dark bands (`gbuffers_water.fsh:275–281`).
3. **SSR source/validity handoff.** Refined below-surface hits immediately fall back, without a signed bank-clearance fade (`gbuffers_water.fsh:35–68`). Use only environment reflection while keeping normal, Fresnel and refraction unchanged. Bands that survive cannot be assigned primarily to SSR source switching; bands that vanish need a positive-hit/independently colored rejected-candidate control before a fix.
4. **Intermediate refraction rejection at real banks.** Any iterate can break at viewport/bank/surface validity (`gbuffers_water.fsh:117–129`); the new clearance confidence is calculated only at a final accepted receiver (`139–146`). A fixed-phase stepped-bank production-main test with a fixed original-UV proxy and smoothly perturbed candidate edge/depth can distinguish a remaining finite jump from the already-GREEN smooth-receiver case. Preserve strict rejection—do not accept invalid geometry to make a continuity test pass.

### Reviewed temporal frame SHA-256

Paths below are relative to `build/quality-v0.4.0/`. The names ending `full-t00` refer to 0.5 s, not literal zero.

| Decoded PNG | SHA-256 |
|---|---|
| `coast-day-full-t00.png` | `628d67069acb04c04b127eb52a7955fc08a777cb1d731a4e82437bf97b8fee7c` |
| `coast-day-audit-t09p90.png` | `7157e51510038017ca77d89af5f6008bb929a508417b5e1e360c8cd8457f8456` |
| `coast-day-full-t10.png` | `4ba93c182e3ae844d5d1b55e76293de6b75779a5bb9b73198b960528bbeeeff1` |
| `coast-day-audit-t10p10.png` | `ea4441f7bcf05e60c4465ee8505df6b6adfaa86dbab1c82c90832d3526bf022b` |
| `coast-day-full-t19.png` | `eadc4ff2b036f1e18159dec96d4880e4bf0bed1a3568675850abdf15ee7a5bc6` |
| `moving-view-full-t00.png` | `af594eba5c6d35ba912f5dc197c4623ed42a3af780fd036524ded9082b2bae54` |
| `moving-view-audit-t09p90.png` | `2d95fda81b214d681ee874a4110a92d19704598a8d42d67ddf99948550785cd0` |
| `moving-view-full-t10.png` | `a81bbe8af5dae1c0b0ce8107ffa609564965b1181cde88a4caada9c74f664cdb` |
| `moving-view-audit-t10p10.png` | `b275a687813531db26a697dc18053878b168d0bb64a1fdbf4c2054bedc017bf3` |
| `moving-view-full-t19.png` | `877c39546079abd1109f3cb0180b23bf17b371291e1835ee7e5269f0c3ca431c` |
| `boat-contact-full-t00.png` | `282b3e1a9cc0d1ce6e3427bc004d888a6e65af39342fa88cbca5a218ca8f2d4d` |
| `boat-contact-audit-t09p90.png` | `3481d05aac12eb4daceb3aedc6c35142d0106b199cb79a9ddff4b3d3bbac53b5` |
| `boat-contact-full-t10.png` | `c29c343216c796258b96983cd116438492795391bb8debc5da171374751a4c57` |
| `boat-contact-audit-t10p10.png` | `693cd1444cf25024c264461a343aab7328d7ea1555c7d1fc4b7f5edc900366a9` |
| `boat-contact-full-t19.png` | `8c32d1304897a968f2bdfcb097af9824bf5b8a289a9d624723d389e9b8051f17` |
