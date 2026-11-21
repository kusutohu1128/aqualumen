# Paired underwater reflection diagnostic contract

The user authorized joint development with actual Claude. The parent integrates and runs checks. Claude authors a bounded diagnostic pack patch. Canonical source and all existing Evidence must be preserved.

## Goal and caller shape

Produce an opt-in TEST pack plus a UUID/pack-hash guarded observer. One actual FINAL invocation yields both the final rendered beauty pixels and the original water-draw reflection classifications at corresponding full-resolution source pixels. A manifest binds program/frame/pack/viewport/camera and raw files. Reject partial or mismatched captures.

The named data shape is `PairedWaterCapture`. Its reflection record is RGBA32F `(route, Fresnel, travel, waterMask)`. Routes are NOT_WATER=0, SSR=1, WORLD_SOURCE=2, KNOWN_UNREADY=3, UNKNOWN=4, PRODUCER_UNAVAILABLE=5. This classifies the actual invoked reflection branch, not a second trace and not why every unsupported model was rejected. Above-water and discarded/nonwater pixels have waterMask0. Use a clear value0 to prevent stale contents. Final beauty stays the production postprocess output, not diagnostic colors.

Freeze resolved wave phase in generated shader copies to17.0 seconds, across vertex displacement, fragment optical normals and receiver-interface geometry. Disable interaction ripple sampling in both paired diagnostic and matching control, record that qualification, and leave production source/defaults unchanged. Daylight and camera control remain restricted to the established V2 UUID. This does not freeze or validate the underlying fluid/contact simulation.

Implementation boundary: assign `time=17.0;` at the entry of `waveSurfaceLocal`, the shared wave evaluator. Keep the real `frameTimeCounter` uniform active: `ReceiverLightingState.capture` requires it for live source-lighting capture. Clouds and other non-wave time remain live. Replacing the global time uniform with a constant would incorrectly disable the source producer and is rejected.

Initialize the secondary MRT output to explicit zero at water-main entry, including nonwater early returns. Disable blending on C12 only; preserve C0 blending. Capture C12 through the actual FINAL sampler with `glGetTexImage` before the quad, and capture actual final output after that same quad. No temporary read FBO is required for C12. The FINAL preview selector must be an active integer uniform equal to zero, not merely assumed from its link default.

The final beauty filter mixes center and four neighbor samples, plus texture-filter footprints. C12 labels each original full-resolution source pixel, not all contributors to a final beauty pixel. Discard leaves earlier contributors untouched; nonwater translucent surfaces can mix C0 while resetting their surviving C12 classification. Record these qualifications rather than claiming one label explains the complete final color.

## Current flow

`gbuffers_water.fsh` computes Fresnel and SSR, consults the world receiver only on underwater SSR miss, and otherwise keeps scatter. `ReceiverRadianceBridge.captureSodium` shades/publishes per-frame first top-face inputs. The normal pack emits only C0 at the water stage. C12 is unused by current production stages. Historical v94 uses `RENDERTARGETS:0,12` but replaces beauty with reason colors, so it cannot be reused as same-frame beauty proof.

`final.fsh` applies the current exposure/tone/neighbor filter/gamma to C0. The old `atlas-joint-probe` brackets exactly the same final quad before/after, restores read state and reads client color pixels, but is hardcoded to older layouts/packs and cannot be installed unchanged for this task.

## Alternatives to compare before coding

A. Passive water MRT C12 plus same-final-invocation full texture/output capture. Keep C0 unchanged. Bind C12 as a real active FINAL sampler through an explicit TEST-only diagnostic preview selector whose normal capture value0 is queried and required. Observer reads the sampler and the final framebuffer at the same invocation; any unsupported color encoding or identity drift rejects.

B. A same-frame diagnostic atlas in FINAL that places beauty and class pixels at an explicitly documented pair of canonical addresses. It must not claim full-resolution unmodified beauty if resolution/address filtering changes. No independent-launch A/B may stand in for same-frame capture.

Prefer direct full-resolution paired capture if it is feasible with the pinned Iris1.8.8 API. Compare alternatives on alignment, no extra trace, production-color invariance, narrow lifecycle footprint and actual resource identity. No implicit texture-flip assumptions.

## Acceptance

- Generated pack transformations are strict-anchor/identity checked, deterministic and fail on unknown source shapes. ZIP outputs are exclusive and do not overwrite dist releases.
- Control has the identical wave/ripple qualification but no observer shader stores; normal production shader files remain unchanged.
- Native NVIDIA compile/link and a controlled color/classification positive/negative test qualify instrumentation, including exact original C0 invariance.
- Actual Minecraft shows the selected pack active without fallback and proves one-frame pairing, finite initialized diagnostic data and listed state restoration. No proxy pass is a full natural visual acceptance.
- Readonly independent review checks pairing and scope before final acceptance.
- No ordinary world mutation or save rollback. Only Aqualumen Lab/V2 may be automated. Build/install only unique TEST artifacts. Restore exact pre-test normal Mods/configs/instance settings and verify ordinary save preservation.
- No source/color/normal correction, performance claim, plant readiness promotion, commit or PR is part of this diagnostic.

Claude may return patch text for new `tools/water_paired_diagnostic.py` and `tools/test_water_paired_diagnostic.py` only. Parent applies it after selecting the design and validating source hashes. Parent owns all observer/runtime files. Existing root GLSL is read-only during this unit.
