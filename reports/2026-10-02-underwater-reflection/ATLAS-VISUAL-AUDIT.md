# Actual underwater atlas v2 — independent visual audit

CPU-only inspection of all three [exported captures](actual-atlas-v2/run.json), their scene metadata, and the shipping-source branch conditions. No GPU/game actions, new measurements or shipping changes. The three PNG/scene JSON files plus run/complete JSON were checked byte-identical to the completed TEST run `underwater-atlas-v2-20261002-2159`.

## Identity and observed images

Diagnostic atlas ZIP SHA256: `210480da8bd06a3265ae09f165f1bf82042344bc3cab32e2e7abf9f639dcdf2b`. This is the current 0.8.4-basis diagnostic, not a shipping visual acceptance. Metadata records approved V2 UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`, seed `308060`, Overworld, active shader/no fallback, focused 1600×900, frame limit 120, 12 chunks, benchmark 0.3.9 and physics 0.3.0. Warmup/sample are 20/5 seconds. Actual first-person camera follows and matches the local player's eye; all three pass the existing strict underwater-head validator and PNG-integrity helper without changing those helpers.

| Capture | Actual eye depth | Camera yaw/pitch | Visual observation |
| --- | ---: | --- | --- |
| [near](actual-atlas-v2/underwater-up-near.png) | 0.499889308 m | −45°/−90° | Broad curved sky window, wrinkled rim, dark exterior remain. |
| [deep](actual-atlas-v2/underwater-up-deep.png) | 3.249889308 m | −45°/−90° | Similar window/rim, deeper cyan attenuation and a few particles; dark exterior remains. |
| [tilt](actual-atlas-v2/underwater-up-tilt.png) | 0.499889308 m | −45°/−65° | Window displaced upward; large dark lower region remains. |

All have camera X/Z `448.5/−383.5`, frozen client/server time 6000 and measured fluid surface Y `62.888889313`. No terrain placement is recorded. Visually, all three upper-right panels are uniform magenta (displayed unknown-column flag), and all lower-right panels are uniform magenta (displayed SSR-miss flag). Bottom-left shows the underwater/water mask with the Fresnel transition. Top-left is a reduced 800×450 panel of post-composite C0 with tone/gamma, without the original final AA taps—not a full-resolution replacement for the original scene. No old rectangular/doubled sky map is visible in these inspected panels; the unnatural-looking rim/dark-region complaint is not resolved.

PNG SHA256, respectively:

- near: `a19b30f565f5caa45a3ee9eca4e1ac2578e522e182140d78543706e0c92550d9`
- deep: `e3867ced9e5a4d66cf6aa1ad10291cf9642169a923cf6aea2ec8094fd1b37992`
- tilt: `d298903e37facb1f459af6a7bd891b5ecae6f8b7712cdb3e48ff0dd674cf9ec2`

## What the flags do—and do not—establish

Physics metadata reports bathymetry ready `1`, 4096 known columns, texture ID `78`, no failure, and current upload counters `5539/8506/11481`. Therefore the displayed unknown flag does **not** demonstrate absent CPU bathymetry. The run's actual storage query covers C0/4/5/6/7/8 only: there is no independent C9/10/11 allocation, final named-sampler/bound-texture proof, or raw pixel readback in this packet. The atlas is downsampled; visually uniform flags are not calibrated full-image counts or a same-frame bathymetry texture join.

Source at inspection: water FS SHA256 `17eb99c946d10aacc3d8a70b60fdbdaa55057c77ae40b2d2f5456c80a8d6fc08`; VS `ad5f0ad33bdc9df04f5c6d0a18bbd87fd1f16442a2b46d836ea79a481451e219`; bathymetry helper `0f663ff635e5e43628dab8d5c3b69f1b3f1e7d19aa9242f9d85c1131dbafd527`.

VS lines 23–36 initialize `waterUnknownWeight=1` and set it to zero only inside `materialId==10000 && worldNormal.y>0.5` when its column query succeeds. FS lines 249–253 AND its own query with `waterUnknownWeight==0`. Thus an underside/downward-face exclusion is a concrete **hypothesis**, not an observed normal or established cause. Sampler/grid delivery, height/coordinate validation, vertex query or interpolation may also reject the column. The helper additionally requires valid four-cell depth/surface data. FS lines 255–265 already use `rasterFacet` unless the final known-column condition succeeds.

A baseline-versus-facet comparison has **not been run** here. If these displayed flags faithfully represent the water invocation, the known-only facet replacement may be inactive/vacuous for these pixels. Equality would not then establish that analytic normals are correct. Displayed SSR misses likewise do not prove an erroneous local tracer: reflected geometry can be offscreen, and the qualified native near-wall repair cannot supply such geometry.

## Single next discriminating seam

One TEST-only same-invocation reason capture: temporarily reuse C9 as `vec4(worldNormal.y, waterUnknownWeight, rawColumnKnown, finalColumnKnown)`. Preserve the existing query result before its AND, without another column lookup or optical trace; leave C0 and all existing decisions unchanged. Prove actual final C9/C10/C11 named units, texture identity, format/dimensions and bounded same-frame readback, using C10's water mask to qualify points. This separates raw-known/weight-one/downward-face, raw-known/weight-one/upward-face, and raw-unknown cases before pursuing only the failing reason. Do not force known true, adopt the facet ablation, or claim natural/temporal/FPS acceptance from this diagnostic.
