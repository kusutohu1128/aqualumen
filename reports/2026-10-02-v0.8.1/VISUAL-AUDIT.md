# Aqualumen 0.8.1 bounded visual audit

The desired natural-water/cloud appearance is **not yet accepted**. The six actual Minecraft PNGs below show a working candidate, but prominent cyan areas, serrated light/dark water boundaries and stylized cloud structure remain. A narrowly verified refraction-search fix is not evidence that the natural shoreline is finished.

## Evidence and scope

Viewed all six original 1600×900 PNGs in [v081-first-bed-smoke-20261002-1335](captures/v081-first-bed-smoke-20261002-1335/run.json). Metadata identifies `Aqualumen-0.8.1.zip`, SHA256 `e8500f10bc66b1b4bc72a3eef1d4467bbe451d421310d1ab61e4f5b6ac841257`, RTX 3080 Ti, default pack options, active shaders and no fallback. [complete.json](captures/v081-first-bed-smoke-20261002-1335/complete.json) lists the six completed scenarios.

This is an image/read-only audit: no GPU tests, game manipulation or source changes were performed for it. The stills do not establish temporal stability, minimum FPS, calibrated water color, cloud-shadow coherence or complete underwater radiance conservation.

## What is visible

| Actual image | Bounded observation |
| --- | --- |
| [coast-day](captures/v081-first-bed-smoke-20261002-1335/coast-day.png) | A broad saturated cyan/turquoise region still dominates the foreground and center. Pointed dark ribbons and abrupt light/dark boundaries remain along both sides. The underlying block steps are visible, but the image alone does not distinguish lawful block/visibility edges from solver, reflection or normal-dependent artifacts. |
| [river-day](captures/v081-first-bed-smoke-20261002-1335/river-day.png) | The shallow foreground remains bright cyan/mint beside large dark patches and a strong serrated boundary. Bed texture and distorted vegetation/reflection are visible. This is not a natural-shore acceptance or proof that all patches share one cause. |
| [ocean-day](captures/v081-first-bed-smoke-20261002-1335/ocean-day.png) | The open-water foreground is a darker blue/gray with broad reflective undulations rather than the coast's large cyan field. Dense horizontal detail persists toward the horizon. A still cannot judge shimmer or wave motion. |
| [underwater](captures/v081-first-bed-smoke-20261002-1335/underwater.png) | A dark blue water column, faint vegetation/bed and particles are visible. The low contrast does not demonstrate realistic underwater illumination or adequate visibility in other conditions. |
| [underwater-up-near](captures/v081-first-bed-smoke-20261002-1335/underwater-up-near.png) | A rounded refracted sky window and strong edge compression remain. The previous inner viewport-shaped quadrilateral and discontinuously repeated cloud map are not apparent in this capture. |
| [underwater-up-tilt](captures/v081-first-bed-smoke-20261002-1335/underwater-up-tilt.png) | The tilted rounded window remains visibly distorted, with dark water outside its rim. No inner rectangular sky seam or second discontinuous cloud map is apparent here either. These two views do not establish that every aspect of the user's original fish-eye concern is resolved. |

Across the sky-bearing images, clouds still resemble repeated rounded boxes/stacked horizontal bands. Their soft shading does not remove that recognizable procedural structure. Natural cloud shape and coherent cloud illumination therefore remain open goals. The sunlight appearance and full-viewport bloom are not calibrated by these six views.

## Older 0.8.0 comparison

The exact retained comparator is [0.8.0 coast-day](../2026-10-02-v0.8.0-runtime/captures/v08-bridge036-ocean-focused-20261002-1036/coast-day.png), with its [metadata](../2026-10-02-v0.8.0-runtime/captures/v08-bridge036-ocean-focused-20261002-1036/coast-day.json). Both coast captures use the same world, camera position `(-191.5, 65.71999988555908, 320.5)`, rotation `(0, 9)` and 1600×900 framebuffer. There is **no resolution change in this particular comparison**.

The broad cyan field and pointed dark shore/water bands remain obvious in both versions; a major visual improvement cannot be concluded from this pair. Capture time, animated cloud/wave phase and contact history differ: the older snapshot reports two contacts/max force 1.7812, while the new snapshot reports one/max force 0.0569. Matching known-column counts do not prove identical bathymetry texture contents or freshness. This is qualitative same-camera comparison, not fixed-phase/pixel-causal A/B evidence.

## Status

The candidate does not visibly reintroduce the old rectangular/double-map underwater-sky artifact in the two inspected upward views. Rounded refraction remains and is not, by itself, proof of either a defect or fully correct underwater optics. Coast/river naturalness and cloud shape remain unresolved. Native transport regressions, actual runtime binding and this visual assessment are separate acceptance boundaries.
