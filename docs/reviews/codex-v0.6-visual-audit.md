# Independent v0.6 actual-image visual audit

Reviewed 2026-10-02 JST. **The sixteen actual Minecraft stills show no obvious catastrophic visual regression, but the convincing natural-shallow-water goal remains unmet.** Coast and river still have conspicuous cyan/turquoise shallow regions and jagged dark/clear bands. The upward underwater views retain the curved sky window without the previously reported viewport-shaped inner rectangle or obvious duplicated cloud/Sun map.

This is a CPU/image-only review. No GPU test, game/UI/lifecycle command, world/configuration change, shader/harness edit or timing job was performed. Only this document was written.

## Evidence and comparison limits

All sixteen original 2560×1440 PNGs were inspected at original resolution from the runtime directory:

`Aqualumen Lab/minecraft/aqualumen-benchmark/runs/water-v0.6-real-view-1440p`.

The root-exported evidence is retained under [`reports/2026-10-02-v0.6.0/real-view`](../../reports/2026-10-02-v0.6.0/real-view/run.json). The recorded active pack is `Aqualumen-0.6.0.zip`, SHA-256 `6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`, with no Iris fallback. The run started `2026-10-01T22:38:01.377989283Z`; its [complete marker](../../reports/2026-10-02-v0.6.0/real-view/complete.json) reports all sixteen scenarios complete at `2026-10-01T22:40:50.198622557Z` and fixture cleanup complete.

The recorded configuration is Minecraft 1.21.1 / Iris 1.8.8 / Sodium 0.6.9, RTX 3080 Ti, 2560×1440 window and framebuffer, render/simulation distances 12/6, VSync off, frame-limit setting 260 and default pack options. Iris and Minecraft clouds are OFF; the pictured clouds belong to the shader pack. The recorded Minecraft GL version is `3.2.0 NVIDIA 580.173.02`; this review does not substitute the native test harness's context version for the actual game context.

All sixteen retained [v0.5 real-view PNGs](../../reports/2026-10-02-v0.5.0/real-view/run.json) were also inspected. They are 1600×900 rather than 2560×1440. Wave/cloud phase, entities and some moving/boat poses differ. This is **qualitative comparison, not fixed-phase pixel causality**, controlled aliasing measurement or a performance A/B.

The new `iris_render_target_storage` runtime record reports `available=true` and `bindingRestored=true`: C0/C4 have actual RGBA32F storage; C5/C8 have RGBA16F storage; C6/C7 are RGBA16F 1024×512 LUTs. This is useful actual-Iris allocation evidence supplied by the recorder. It is not proof of calibrated radiance, complete transport conservation or visual realism, and this reviewer did not query the live renderer.

## Visual observations

| Scene(s) | What the original PNGs show | Bounded assessment |
|---|---|---|
| [Coast day](../../reports/2026-10-02-v0.6.0/real-view/coast-day.png) | Broad bright turquoise/cyan shallows with visible bottom blocks/vegetation. High-contrast dark-gray reflective ribbons cut through clearer water with serrated edges; dense bright speckles/edging remain near the sand shoreline. | Dominant shallow-water appearance problem remains, broadly like v0.5. The still cannot identify which particular tracer, reflection or source transition causes each band. |
| [River day](../../reports/2026-10-02-v0.6.0/real-view/river-day.png) | Mint/cyan bottom regions alternate with gray-blue reflective patches and distorted vegetation reflections; the bank transition remains strongly banded/jagged. | No convincing natural-river visual acceptance. Higher resolution does not make this a causal comparison with the old image. |
| [Ocean day](../../reports/2026-10-02-v0.6.0/real-view/ocean-day.png) | Dark blue/gray open water, cloud gradients and elongated contour-like/marbled ripple reflections; some bottom/kelp hints remain at shallow edges. | No missing ocean or uniformly emissive cyan sea. Long reflective ribbons still look stylized. |
| [Dusk](../../reports/2026-10-02-v0.6.0/real-view/ocean-dusk.png) | Orange/gold sky and corresponding warm water response retain contrast against dark wave shapes. | No whole-viewport white bloom/clipping catastrophe. This pose does not provide a clearly resolved direct Sun disk for appearance calibration. |
| [Night](../../reports/2026-10-02-v0.6.0/real-view/ocean-night.png) | Very dark navy water with faint kelp/bottom silhouettes and cloud structure. | No bright cyan night-emission field; dim playability remains a separate issue. Broadly similar to v0.5. |
| [Rain](../../reports/2026-10-02-v0.6.0/real-view/ocean-rain.png) | Gray overcast sky and dark gray water, with dense long rain streaks over the scene. | Weather appearance retained; no full-frame light explosion. A still does not verify rain-driven ripple motion or physical drop interaction. |
| [Underwater forward](../../reports/2026-10-02-v0.6.0/real-view/underwater.png) | Blue low-contrast haze, faint kelp/bottom and square particles. | Not a blank/black render, but visibility and color are not measured real-water optical calibration. |
| [Up near](../../reports/2026-10-02-v0.6.0/real-view/underwater-up-near.png), [up deep](../../reports/2026-10-02-v0.6.0/real-view/underwater-up-deep.png), [up tilt](../../reports/2026-10-02-v0.6.0/real-view/underwater-up-tilt.png) | A large curved Snell-window-like opening with coherent clouds; the deeper image is bluer/hazier and the tilted rim shifts. A single small bright Sun spot is visible within the opening. The rim has thin bright/speckled portions. | No central rectilinear viewport boundary or obvious repeated cloud/Sun map found. Curved compression remains, as it already did in v0.5. No claim of complete angular validation or conserved underwater radiance/étendue follows. |
| [Moving view](../../reports/2026-10-02-v0.6.0/real-view/moving-view.png), [boat contact](../../reports/2026-10-02-v0.6.0/real-view/boat-contact.png) | Water has elongated layered/marbled reflection ribbons; the boat bow is visible in the contact image. | Rendering is nonblank, but neither still demonstrates temporally stable highlights, natural wakes or contact-caused wave propagation. |
| [Cave water](../../reports/2026-10-02-v0.6.0/real-view/cave-water.png) | Muted water alongside stone and locally readable lush vegetation. | No obvious bright Earth-sky rectangle or uniform cyan emissive panel in this cave view; not an all-cave transport test. |
| [Glass layers](../../reports/2026-10-02-v0.6.0/real-view/glass-layers.png) | Multiple gridded transparent slabs retain visible ocean/sky behind them. | No opaque-black/missing-glass catastrophe here. Arbitrary ordering, viewing angles and physical multilayer energy are not certified. |
| [Nether](../../reports/2026-10-02-v0.6.0/real-view/nether-view.png), [End](../../reports/2026-10-02-v0.6.0/real-view/end-view.png) | Red/orange fire/lava and dark rock in Nether; dark purple sky, pillars and readable terrain in End. | No Overworld cloud/Sun contamination observed; dimension compatibility retained in these views. |

No inspected scene has an obvious full-frame magenta error, whiteout, missing render or newly visible underwater rectangle. This is limited compatibility evidence, not a photorealism score.

## Sun, bloom and numerical-fix interpretation

The brightest visible direct Sun example in this set is the small single spot in the three upward underwater captures. It does not bloom across the entire viewport or erase the cloud/window structure. Day/dusk open-water poses chiefly show sky and water response, not a resolved disk, so they do not establish direct-disk quality over all elevations, fields of view or reflection angles. LDR screenshots cannot independently verify the pre-tonemap HDR range or integrated subpixel solar energy.

The bounded native visible-bed source-loss and solar-radiometry work should be reported alongside these images, **not used as a substitute for them**. Seeing broadly similar v0.5/v0.6 coast bands does not disprove a narrowly demonstrated solver fix; nor does that fix prove the unresolved natural shoreline is now correct. No source-specific causal attribution is made from these phase/resolution-mismatched stills.

Complete underwater radiance/étendue conservation, arbitrary bank-side water membership, wave-normal/geometric-surface agreement and bent-ray visibility remain separate approximation/verification boundaries. This visual review adds no claim that an omitted refractive index-squared radiance factor or full medium transport has been solved.

## Remaining quality priorities

1. **Natural coast/river radiance handoff.** The persistent cyan shallow patches and serrated reflection/clear-water bands are the clearest visible quality gap. Continue source-provenance/visibility diagnosis at real stepped shores, distinguishing valid reflection, refracted receiver, proxy and actual occlusion edges; do not treat indiscriminate desaturation or smoothing of lawful edges as a physical fix.
2. **Water reflection structure and motion acceptance.** Elongated marbled ribbons remain conspicuous in ocean, moving and boat views. A controlled natural camera-motion sequence is needed to separate stable wave geometry from highlight aliasing and traced-source handoffs. One PNG named `moving-view` does not establish temporal continuity, and a boat still does not establish a realistic wake.

This reviewer did not recalculate frame CSVs or conduct performance measurements. The root's separate [run report](../../reports/2026-10-02-v0.6.0/real-view/RESULTS.md) contains the short recorded timing observations; none should be promoted here to a guaranteed live 60 FPS floor or causal speed comparison with 1600×900 v0.5.
