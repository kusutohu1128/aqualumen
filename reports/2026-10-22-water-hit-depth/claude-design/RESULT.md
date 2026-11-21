# Aligning underwater first-hit depth and eye attenuation (hit2): explanation and design

## Overview
The hit1 candidate solves the continuous water surface at `opticalPoint`. It then uses that point for the normal and for the reflection/refraction start points. Everything that measures distance to the surface still uses the coarse polygon:
- **Hardware depth:** it comes from the rasterized fragment, `gl_FragCoord.z`.
- **Composite:** it rebuilds `distanceToEye` from `depthtex0` (`shaders/composite.fsh:23-26`) and applies the eye-to-surface Beer attenuation once (`:49-52`).
- **gbuffers_water:** `straightPath` (`shaders/gbuffers_water.fsh:276`) and `shadowVisibility(worldPosition,n)` (`:345`) still use the raster point.

The surface is shaded at one point and attenuated as if it were at another.

## Key concepts
- **Same ray.** `continuousWaterPoint` searches along the line from the eye through the pixel's raster point (`tools/water_continuous_interface_test.glsl:21`). The solved point projects back to the same pixel center. Only its depth along the ray changes, by up to `heightBound/ray.y`.
- **Depth is a transport record.** For an underwater eye, composite's single Beer term is the eye-to-surface leg. The refraction term from gbuffers carries no Beer (`:420`, where `refraction=behind`). Reflection applies its own Beer from its origin (`:449-451`). Once the reflection origin moves, the eye leg has to end at the same point.
- **`depthtex1`** is Iris's copy of depth before translucents. It is the opaque reference in both programs and must not change.

## How it works now (hit1)
`main` computes `viewPos`, `straightPath` and `opaqueDepth` from the raster point. Inside the eligible branch (`underwater && footprint*1.25<=0.035 && column≥0.8`) the solver sets `opticalPoint`. The wave and normal are then evaluated there, `opticalViewPos` feeds both traces, and receivers start from `opticalPoint+n*0.06`. Composite later reads `depthtex0`, which still holds the raster depth.

## Where things live
- Candidate generator: `tools/water_continuous_candidate.py`. It patches the hit1 zips by anchor with `probe.replace_one` and never touches `shaders/`.
- Solver: `tools/water_continuous_interface_test.glsl`.
- Readback: `hit1/observer-sources/.../GlReadback.java`. `sampler()` hard-requires `format==34836`, i.e. RGBA32F (`:45`). `rawFloats` rejects non-finite values.
- Channel schema: `PairedObserver.java:117,217`.
- Native harness: `native-opticalhit1-zoom3/water-paired-native-zoom.cpp`. It currently runs with `GL_DEPTH_TEST` disabled and no depth attachment (`:94-95`).

## Gotchas
- If any path writes `gl_FragDepth`, every path must write it, including the non-water `return` at `:261-266`. The write also turns off early-Z for every translucent-terrain fragment. Never add `early_fragment_tests`, because it would silently discard the write.
- `/* DRAWBUFFERS:02 */` maps `gl_FragData[1]` to colortex2. Use `RENDERTARGETS: 0,2` and say so explicitly.
- Writing depth can change which fragments pass the depth test, both against opaque geometry and against later translucents, particles or the hand.
- Composite treats `depth==opaqueDepth` as "no water in this pixel". A corrected depth exactly equal to the opaque depth would be misread, so the comparison must be strict.
- The depth range cannot be assumed to be [0,1] with plain perspective. Only a native fixture plus the actual captured depth bytes settle that.
- No derivatives may be taken of `opticalPoint`, because it comes from a divergent branch.

## The two alternatives

**A. Write `gl_FragDepth` as the projected `opticalPoint`.**
- **Pros:** The depth buffer stays the single authority. Composite is untouched, and every later `depthtex0` reader sees the same first hit. No new data path is needed.
- **Cons:** Visibility can change, and early-Z is lost.
- **Opaque risk:** The solve bracket ignores opaque geometry. A crest can land behind a block within about one bound of the surface, such as a cave ceiling 0.11 m above the water, a pillar top, kelp or a boat. A raster fragment hidden behind such a block could also become visible.
- **Fix:** Accept the solution only if both the raster depth and the projected optical depth are strictly in front of `depthtex1`, and the optical depth is greater than 0. Otherwise fall back to the raster value for everything. With that guard, pass/fail against opaque geometry is unchanged by construction.

**B. Raster depth unchanged; composite reads an authoritative optical record.**
- **Pros:** No visibility change and no early-Z loss.
- **Cons:** It needs a new MRT in the production path of both packs, which is an extra producer write you ruled out. It also needs an ownership key, an exact match on the stored raster `gl_FragCoord.z`, to reject records left stale by later translucents. Every `depthtex0` consumer other than composite stays inconsistent. And the observer would be checking the same channel composite consumes, so it would not be independent.

**Recommendation: A with the opaque guard as the candidate's transport.** B's shape is kept only as passive instrumentation: in the paired pack, composite writes what it actually applied into C2.

## Caller usage and signatures (sketch, not implemented)
```glsl
// helper (appended to water_continuous_interface_test.glsl or a hit2 sibling)
float opticalWindowDepth(vec3 relativePoint);            // gbufferProjection*gbufferModelView, z/w*0.5+0.5
bool  opticalDepthAdmitted(float rasterZ,float opticalZ,float opaqueZ); // rasterZ<opaqueZ && opticalZ<opaqueZ && opticalZ>0
```
Changes to the hit1 water source, each made by `replace_one` with a single anchor:
```glsl
void main() { gl_FragDepth=gl_FragCoord.z;               // every path, including the non-water return/discard
...
if(continuousStatus==0) {                                 // inside the solve block, BEFORE the wave is evaluated
    float z=opticalWindowDepth(solved);
    if(opticalDepthAdmitted(gl_FragCoord.z,z,opaqueDepth)) { opticalPoint=solved; opticalDepth=z; }
    else continuousStatus=4;                              // 4 = depth/occlusion rejected → everything stays raster
}
...
vec3 opticalViewPos=...;                                  // existing hit1 line
if(continuousStatus==0) {
    straightPath=opaqueDepth<0.999999?clamp(length(opaquePosition-opticalViewPos),0.0,48.0):48.0;
    gl_FragDepth=opticalDepth;
}
float visibility=shadowVisibility(opticalPoint,n)*skyAccess;
```
- For any status other than 0, `opticalPoint==worldPosition` and the depth write equals `gl_FragCoord.z`, so the fragment is meant to behave exactly as in hit1.
- `opticalDepth` is declared next to `opticalPoint`.
- In the paired composite only: `/* RENDERTARGETS: 0,2 */`, then `gl_FragData[1]=vec4(distanceToEye, isEyeInWater==1?transmission:vec3(-1.0))`. The values are always finite. C0's math is unchanged.

## Which origins move
**Moved in this unit:**
- Hardware first-hit depth, and through it composite's `distanceToEye`, transmission and scatter weight.
- The `straightPath`/`initialPath` origin of the refraction trace.
- The shadow-visibility point that feeds `incidentIrradiance` and `scatter`.

**Deliberately left outside:**
- **Wave inputs:** `footprint`, `rasterFacet`, the filter width, `normalVariance` and the eligibility rule. Moving them would change the waves.
- `v`: the direction is the same ray, so only floating-point rounding differs.
- `lightmap`/`skyAccess`: interpolated from vertices.
- The reflected-receiver `incidentDepth` from `absolutePosition.y` (`:442`): it is a horizontal-surface approximation of the receiver's own sun path, which belongs to the R2/source-radiance work.
- `verticalDepth`, foam, `receiverSolarTransmission`, caustics and the trace `surfaceY` arguments: all above-water only.
- Ripples: zero in this domain.
- Composite's `depth==opaqueDepth` receiver branch and its `aqualumenGrid.w` incident depth.

## Artifact ownership
| Artifact | Owner | Lifecycle |
|---|---|---|
| `opticalPoint`, status 4, depth write, origins | hit2 water source in both zips (control and paired), from new `tools/water_depth_candidate.py` pinned to the hit1 zip SHAs | per fragment |
| Main depth → `depthtex0` | Iris; the water program owns only its own fragments | per frame |
| `depthtex1` | Iris copy before translucents | must stay byte-identical |
| C2 (paired only) | composite: (distance, transmission RGB). gbuffers' C2 geometry write may stay, since composite overwrites it, so the water instrumentation is otherwise byte-equal to hit1 | composite → FINAL |
| C1, C3, C12–C15 | unchanged hit1 meanings | |
| FINAL preview-only branch | paired pack; references `depthtex0`, `depthtex1`, `gbufferProjectionInverse`, `gbufferModelViewInverse` so they stay active | |
| Observer 0.1.0-hit2 | new `GlReadback.depthSampler` and `matrix(program,name)` (`glGetUniformfv`, type 35676); colour guard stays strict RGBA32F | read-only, state-preserving |
| Analysis | new `.audit/` script, hash pinned; new report directory; no overwrites | |

**`depthSampler`:**
- Accept only GL_DEPTH_COMPONENT24, GL_DEPTH_COMPONENT32F, GL_DEPTH24_STENCIL8 or GL_DEPTH32F_STENCIL8 (33190, 36012, 35056, 36013), base level 0 and the exact size. Record the actual format. Anything else fails, with no fallback.
- Require `TEXTURE_COMPARE_MODE==NONE`.
- Read with `glGetTexImage(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT,GL_FLOAT)` inside `preserving(REAL)`.
- Alias checks: `depthtex0`, `depthtex1` and all colour textures must be distinct.

## Tests

**1. Native fail-first (minimized), extending the zoom3 harness with a real depth path:**
- Attach a DEPTH_COMPONENT32F buffer. Pre-fill it with the fixture's opaque depth, with `GL_LEQUAL` and depth mask on.
- Draw the zoomed underwater quad. Add a composite-like pass that rebuilds the distance from depth and writes it to RGBA32F. A fixture-only target carries `|opticalPoint−eye|`.
- **Validity first:** at least 10⁴ pixels must solve with status 0, or the run is invalid, not passed. This is the hit1 lesson about fixtures where nothing was eligible.
- **Expected:** with hit1 shaders, mismatch above the depth-quantization tolerance on more than 0 pixels (this must fail). With hit2, 0 mismatches.
- **Tolerance per pixel:** about 2·(d²/near)·ulp(z) + 1e-6·d, with `near` taken from the matrix.
- **Sanity:** for status other than 0, `opticalWindowDepth(worldPosition)` must equal `gl_FragCoord.z` within one ulp. This validates the depth formula and range.

**2. Native opaque-occluder test.**
- **Setup:** using hit1 C3, put an opaque quad in the pre-filled depth in two places. (a) Between the raster and optical depths where the optical point is farther. (b) Between them where the optical point is nearer.
- **Expected:** the set of covered pixels equals hit1's exactly, and the guarded pixels report status 4 with raster depth.
- **Negative control:** an unguarded variant must fail both cases.
- This shows the guard works natively. It does not prove anything about Iris attachments.

**3. Actual same-FINAL checks** (Lab UUID b22dbccb-2970-41e6-847f-f183b1ec923d only; frozen 17 s, ripples 0, the existing near and deep poses):
- **New baseline:** run a "hit1d" pack, which is hit1 shading plus the hit2 observer, composite C2 and depth readback. This is new data, not a rerun, because hit1 never captured depth. It must show nonzero depth/distance mismatches on status-0 pixels (the in-game fail-first).
- **Depth matches optical point:** for status-0 pixels in hit2, `depthtex0` equals the projection of C3 using the captured matrices within the tolerance above, for the format actually read.
- **Distance chain:** C2.x equals |C3.xyz − eye|, and for other statuses |C1.xyz − eye|, where eye = `gbufferModelViewInverse`·0. C2.x also matches the rebuild from `depthtex0`.
- **Transmission:** C2.yzw equals `waterTransmission(C2.x)` within float ulps.
- **Unchanged against hit1d:** `depthtex1` is byte-identical. `depthtex0` is byte-identical outside status 0. C1 is byte-identical.
- **Counts:** report the number of status-4 pixels and the full distribution of depth shifts.
- **Passivity:** paired C0 equals the unobserved hit2 control C0 for every case.
- **In-game occluder:** if no opaque geometry falls inside the bound band in the Lab frames, the in-game occluder result is `null` (not exercised), not passed. A dedicated Lab-only scene variant is your call.

**Not claimed:**
- The shadow-point move has no in-game channel. It is checked only by source diff and the native fixture, so it stays open evidence.
- Early-Z/performance cost: frame times are recorded, but no gate is passed.
- Other translucents, particles and hand interactions with the corrected depth: unknown/shallow/contact/cave worlds, R2, physical, visual and release gates all stay open.
- Ordinary saves and configs stay untouched. After the run, restore the normal instance to 0.6/physics 0.2 and stop the client.

I read 16 files and used no subagents or commands. Plan mode asked for a plan file, but I had no write tool, so this message is the whole handoff. The paired pack's `shaders.properties` is inside the zip and I didn't read it. Before trusting C3, C12 or C14, check that it turns blending off for those buffers, since their alpha channels hold data.
