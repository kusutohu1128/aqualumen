# Independent v0.5 incident-Sun-leg review

Read-only optical/source review, 2026-10-02. **The minimal direct-Sun incident Beer leg is a sound bounded first slice for a flat bed beneath a local horizontal water plane.** It does not establish complete submerged lighting, water membership, bent-ray shadows, arbitrary receiver normals or a solution to the real cyan/jagged shore appearance. Those limits do not invalidate its deliberately narrower first test.

No GPU/game/control/lifecycle operation or shader/CPP edit was performed by this reviewer. Only this document was added. Native results below are independent readings of the harness owner's logs/source, not this reviewer's GPU executions.

## Evaluated and pending

| Item | Evidence/status | What it establishes |
|---|---|---|
| Component replacement and ordering | Source reviewed: `composite.fsh:41–52`, `water.glsl:26–33` in the Beer-only candidate identified below | Replace the raw receiver-Sun base and its focusing contribution, before one existing eye leg; ambient/Moon/block components are not incident-Sun attenuated. |
| Normal Sun, flat bed, incident depth +2 m | Harness owner's `build/water-incident-depth-red.log` / `-green.log`, production composite main | RED response ratio is 1; GREEN ratio agrees with independent Beer references and remains positive. |
| Absolute normal-incidence entry Fresnel | Harness owner's `build/water-entry-fresnel-red.log` | A useful subsequent RED: the Beer-only version omits entry reflection. No entry-Fresnel GREEN is claimed in this snapshot. |
| Oblique Sun, arbitrary receiver normal/shadow, dry pocket/other pool | Not demonstrated by the first test | Explicit limits/next controls, not assumed failures in the tested flat-bed case. |
| Real-world v0.5 coastline/temporal appearance | Not evaluated here | No visual acceptance or FPS guarantee. Above-water refraction remains outside the inspected composite-only slice. |

Beer-only source snapshot (candidate bytes, **not an installed/release pack identity**):

| File | SHA-256 |
|---|---|
| `shaders/composite.fsh` | `3d12aea1221fb2773db71c5408bdce8c2b29de5bae98f2584577f785434cf6c1` |
| `shaders/lib/water.glsl` | `66795b589229c89c478fc15880853f0216b5ffda087ca9e11963eccac431202e` |
| `shaders/gbuffers_water.fsh` | `ae9c2989deb53b27129b65367c1cf4969e4d3b9a314b3838fca483c8327e3c04` |
| `shaders/lib/lighting.glsl` | `16cf5a6c9b78b70b7cef735a58628742dffe8249fdba8443ede4a2a088ab2e34` |
| `physics-mod/dev/aqualumen/physics/Contacts.java` | `ec602293531162ba70603b9f42f1d3039242745f9d2ba6ddf8693544a7e46b9c` |

The root is separately developing the entry-Fresnel follow-up. Line/hash references above intentionally identify the first Beer-only slice rather than silently claiming its later status.

## Transport contract

Let `C` be current raw receiver RGB, `S` the paired, clamped **air-lit** direct-Sun attribution from C8, `d` the receiver depth beneath the local plane, and `K=1+0.65*(focus-1)`. The minimal replacement is:

```
sunDown = refract(-sunUnit, up, 1/1.333)
incidentLength = d / (-sunDown.y)
Tsun = exp(-sigma_t * incidentLength / WATER_CLARITY)
Cincident = (C - S) + S * Tsun * K
Ceye = Cincident * Teye + scatterEye * (1 - Teye)
```

This is an incident **direct beam** followed by an independent outgoing eye path. The multiplication of beam transmittance along separate legs is consistent with homogeneous-medium extinction; it does not add missing in-scattering, multiple scattering or bottom bounce. [PBRT's transmittance treatment](https://pbr-book.org/4ed/Volume_Scattering/Transmittance) describes Beer attenuation as extinction along a ray, distinct from in-scattering.

Attenuating only `S*(focus-1)` leaves the dry base Sun unchanged and would not fix the diagnosed omission. Attenuating all of `C` instead incorrectly darkens unrelated ambient/block/Moon illumination. Pre-attenuating C8 and then applying the same incident leg again double-counts it. The reviewed caller correctly replaces the complete Sun component once and leaves C8 raw/immutable.

The helper uses normalized `sunDirection()` and the air-to-water Snell direction, not `d/sun.y`. For a flat air-to-water surface, the refracted downward cosine remains at least about 0.6612 as the air Sun approaches the horizon; the tiny denominator floor does not impose an artificial grazing path in that model. Direction and energy partition are separate quantities in [PBRT's Snell/Fresnel description](https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission).

## First test is meaningful, but not an absolute transport proof

The actual fixture links expanded production composite main, sets public wave height to zero and clarity to one, varies local plane height for 1.5 versus 3.5 m incident legs, and fixes the outgoing eye leg at 1 m. Its lit/unlit pair changes **C0 total color and C8 Sun attribution coherently**; zero-C8 backgrounds cancel, and repeated renders are checked. Varying only C8 with a fixed C0 would instead measure `(Tsun-1)` replacement sensitivity, not the direct-Sun transmitted response.

Observed first GREEN receiver-Sun deltas are `(0.0898658,0.121284,0.0916219)` at 1.5 m and `(0.0473856,0.102323,0.0854277)` at 3.5 m. Their ratios `(0.527292,0.843665,0.932394)` match the independent `exp(-sigma_t*2)` references. The test cannot pass by deleting all Sun because it requires positive responses. Its zero-source/background values stay unchanged.

This ratio cancels any constant entry Fresnel factor, so its success cannot certify entry energy. For IOR 1.333, calculated normal-entry reflectance is `F0=((1-1.333)/(1+1.333))²=0.020373187841971414`. The subsequent RED's expected deltas are about `(0.0880349,0.118813,0.0897553)`, rather than the Beer-only deltas above. Testing that absolute `(1-F0)` factor separately is the appropriate next slice, not a reason to mislabel the already demonstrated Beer-depth response.

## Oblique beam, receiver normal and shadow limits

For a horizontal interface and horizontal bed, Beer-only incident depth still uses the correct **refracted path length** at oblique Sun. At air cosine 0.5, the calculated water cosine is `0.76020654`; an additional 2 m vertical depth means `2.63086398` m beam path and expected extra Beer ratios about `(0.430901,0.799616,0.912032)`. These are calculated proposed-control values, not GPU results.

C8 nevertheless already contains `max(dot(receiverNormal,sunAir),0)` and an air-direction shadow (`lighting.glsl:9–13`). Multiplying it by Beer cannot reconstruct the refracted receiver cosine or visibility. It cannot recover a valid underwater Sun term from a zero air-normal/air-shadow term, and dividing by that zero is unsafe.

**Reviewer derivation for a later collimated-beam extension:** if `B` denotes irradiance normal to the air beam, `ca`/`ct` are the interface air/water cosines, and `sWater` points from the receiver back toward entry, a uniform flat interface implies receiver irradiance proportional to:

```
B * (1-Fair) * (ca/ct) * max(dot(receiverNormal,sWater),0) * Tsun
```

For a horizontal bed, the receiver cosine is `ct`, so this reduces to `B*ca*(1-Fair)*Tsun`: no extra power is gained merely by bending the beam. Simply replacing the old air normal cosine with the refracted cosine without its beam-area factor would make flat beds too bright at oblique Sun. This is a flux-conservation inference, not functionality present in the minimal patch. PBRT distinguishes refracted radiance/solid-angle scaling from conserved radiant power; **do not add an arbitrary IOR-squared multiplier to the already receiver-integrated C8 component**. [PBRT's refractive transport discussion](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF#NonSymmetricScatteringandRefraction)

A future shadow model also needs the air leg to the entry point and the bent water leg to the receiver, including submerged blockers. Reusing the existing straight-air receiver shadow is a declared approximation; multiply-only correction cannot repair a receiver hidden to that old direction. Wave focusing currently uses its own inverse-map/curvature approximation, while incident Beer uses the mean horizontal plane: they are not an exact shared bent ray through the animated surface.

## Unsafe gating and bounded applicability

- **Underwater eye is not underwater receiver membership.** `isEyeInWater==1`, matching opaque depth and `d>0` say where the eye/receiver lie relative to one plane, not that the entire incident or outgoing segment is water. Dry cave pockets, a receiver across a bank, side exits and separate pools remain possible. Do not call the Sun leg physically proved there.
- **Active plane is local/recent state, not a world water mask.** `Contacts.java:68–83` finds a contiguous nearby water column; `110–155` chooses a local plane from nearby contacts/camera probing and can keep it active for ten seconds. The uniform supplies a 64 m grid, but the reviewed composite gate does not check receiver/entry grid coordinates. Even an in-grid check alone would not prove continuous water membership. A hard grid cutoff would also require a transition/recenter control; it must not introduce an unexplained camera-following rectangle.
- **Coordinates and half-space must agree.** The grid plane and `receiverWorld` are in the same camera-relative basis (`Contacts.java:154`), so `grid.w-receiverWorld.y` is the correct difference. Adding camera Y to only one creates a large erroneous depth. Above-plane receivers and nonpositive Sun should stay unchanged; finite/depth-pair validity must remain strict. The Beer-only helper returns identity at `d<=0`, continuously matching the no-incident-water limit. A future Fresnel gate introduces an actual medium-assignment boundary and needs an explicit wet/dry applicability policy rather than an arbitrary blur.
- **Depth equality is not material/source identity.** The current exact same-pixel depth/C8 pairing must stay intact, but non-depth-writing translucent layers or co-planar depth collisions can change C0 while C8 still describes another receiver. Clamping S to current C limits subtraction; it does not prove the attribution belongs to that visible material.
- **The scope is direct Sun, not all underwater light.** No diffuse-sky incident leg, refracted ambient quadrature, block-light water path or bent lunar shadow is established. Above-water confirmed-hit/proxy refraction still follows the 0.4 caller in this snapshot; the underwater composite result must not be reported as a complete repair of above-water coastline appearance.

Recommended narrow follow-ups, after the separate normal-entry absolute test: an oblique horizontal-bed flux/path control; zero-Sun and unchanged non-Sun controls; above-plane/inactive/non-Earth/nearer-layer bypasses; and independently varied wet/dry receiver applicability. Arbitrary-normal and bent-shadow cases belong to another explicit transport slice unless the necessary normal/visibility/source data are supplied. No first-slice demand for full-world photon transport, fluid bathymetry or photorealism is made here.
