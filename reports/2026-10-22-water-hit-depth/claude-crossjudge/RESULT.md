I followed your read-only limits: no subagents, commands or writes. That also means I didn't create a plan file. I read the two design files plus targeted parts of `shaders/composite.fsh`, `shaders/gbuffers_water.fsh` and `shaders/shaders.properties`.

## 1. Opaque visibility: pick the unguarded contract

**Both straddle cases.** Take an underwater eye, the raster depth `zr`, the solved depth `zo`, and an opaque depth `zp` strictly between them.

- **(a) `zr < zp < zo`.** The raster surface is in front of the opaque, but the solved surface is behind it. In the continuous model the opaque point is below the solved interface, so it is underwater and should be seen through water.
  - Unguarded: the late test fails, the opaque colour stays, and `depth0 == depth1`. Composite then applies the receiver branch and the eye-to-opaque Beer term. That is consistent with the model.
  - Guarded: status 4 draws a raster interface in front of an object the model says is submerged.
- **(b) `zo < zp < zr`.** The solved trough is nearer than the opaque. In the model the opaque point is in air above the interface, so water should win.
  - Unguarded: the fragment passes, its depth is `zo`, and composite's eye leg ends at the shaded point.
  - Guarded: it keeps showing the opaque object, which the model says is hidden.

**Verdict.** The guard doesn't repair primary visibility. It keeps the coarse-mesh approximation exactly where the two models disagree. It also adds a new artifact: a contour where status 0 changes to status 4 along every opaque intersection, with optical normals on one side and raster normals on the other.

There is also a structural problem with the guard. It tests `depthtex1`, but the hardware tests the live depth buffer. By the time water draws, that buffer may already hold earlier translucent depths, so the guard isn't even checking the same thing the hardware checks.

**Fully blocking ceiling.** This is the vanilla case: water surface at 8/9 of a block with a solid block above, leaving about 0.11 m of headroom. With a larger `heightBound`, the unconstrained wave crosses into the ceiling.
- Unguarded shows ceiling patches seen through water. That is what you would see physically in a water–ceiling contact region, where there is no air interface.
- The guard hides this by drawing a raster interface, so the pixel claims an air gap the model doesn't have.

The real defect is that the wave isn't contained. That belongs to a later wave-containment or eligibility unit, such as requiring headroom ≥ `heightBound`. It shouldn't be patched per pixel with a visibility guard. Report the straddle counts as a measured symptom of that model domain, not as a pass.

**Could anything make the unguarded option unsafe?** Only if, at the water draw, the depth test is off, the depth function isn't LESS or LEQUAL, the depth mask is off, or opaque geometry is missing from the live depth buffer. In every one of those cases, raster visibility was already wrong, and `depthtex1` is a copy of that same buffer, so the guard gives no protection. The one real risk is shader-declared: see below.

**Exact pipeline roles:**
- **Early fragment tests:** forbid `layout(early_fragment_tests)`. It would test against `gl_FragCoord.z` and drop the write, quietly turning back into raster visibility.
- **Conservative depth:** forbid `depth_greater` and `depth_less`, because both directions happen and hi-Z would wrongly cull fragments. Use the default `depth_any`.
- **Early-Z cost:** writing depth turns early-Z off for the whole translucent-terrain draw. The existing `discard` at `gbuffers_water.fsh:263` already weakens it.
- **Depth writes:** the late test of `gl_FragDepth` against the live buffer chooses the winner. Initialise `gl_FragDepth = gl_FragCoord.z` on every path, including `:261-266`.
- **Tie with the opaque:** under LEQUAL, `zo == zp` lets water win while composite's `depth==opaqueDepth` reads it as "no water". Treat exact equality as a representational rejection and count it. This is a tie-break, not a visibility guard.
- **Blending:** `blend.gbuffers_water=SRC_ALPHA…` runs only after the depth test passes. A failed fragment changes nothing, including C1 and C3. A passing one blends over whatever opaque colour is already there, which is the correct background in both cases. Data targets (C3, C12–C15) need per-buffer `blend…=off`.
- **Primitive coverage:** fragments exist only where the coarse mesh rasterises. `gl_FragDepth` can't create coverage, so silhouettes and crests beyond the mesh edge stay missing. The same-pixel requirement only moves depth along the ray.

**Target semantic contract:**
> Wherever the mesh covers a pixel, the stored depth is the continuous model's first hit on that pixel ray, and hardware depth ordering decides visibility. Composite's eye leg is reconstructed from that stored depth.

This matches the parent's preference. Proof must come from native straddle tests in both directions, which must fail on hit1, plus actual evidence; see the open gates.

## 2. Reflected-source `incidentDepth`: defer it

`gbuffers_water.fsh:442` (and `:408`) use `absolutePosition.y` as the height of the Sun's entry interface. The Sun actually enters the surface somewhere above the receiver, at a different xz. So neither the raster Y nor the optical Y at this pixel is correct. Moving it would swap one wrong local height for another, change the output, and muddy what the depth unit can be credited with.

**Smallest coherent unit:**
- primary `opticalPoint`, which is already in hit1;
- `gl_FragDepth`, which composite's eye Beer term picks up through `depth0` with no code change;
- the `straightPath`/`initialPath` origin;
- the `shadowVisibility` point;
- reflection and refraction origins, which already moved in hit1.

Keep raster `footprint`, derivatives, eligibility, `skyAccess`/`lightmap`, and the trace `surfaceY` arguments, which don't apply underwater. Label `:442`/`:408` honestly as "source-radiance interface height = raster plane (approximation, R2 scope)".

## 3. Observation schema: matrix readback isn't needed

Distance is the only quantity composite takes from depth underwater. Two baseline-plus-candidate loops close the chain using the actual uniforms in each program:

1. **Baseline (raster depth):** C2.x = |C1.xyz| for all water pixels. This proves composite's actual inverse projection matches the hardware raster transform, and that the eye is at the relative-world origin. A bobbing or translation offset would show up as a systematic, falsifiable mismatch.
2. **Candidate:** `depth0` = C3.w, within 0 for D32F or 1 quantum for D24, using the format actually read. This shows the written depth is the computed one. Then C2.x = |C3.xyz| shows that depth reconstructs the point's distance, and C2.yzw = `waterTransmission(C2.x)`.

Direction is only covered by the shader's own same-pixel check, so it rests on the native fixture. That is a small, honestly labelled gap, not a meaningful one.

**Straddle detection needs no extra channel:**
- (a) baseline C3.w > `depth1` at pixels where the raster is in front;
- (b) pixels where the candidate has C3 coverage and the baseline doesn't.

This requires a known per-frame clear sentinel on C3.

**Schema:**
- **C1:** raster point, unchanged.
- **C3.xyz:** `opticalPoint`.
- **C3.w:** projected depth, −1 if ineligible, −2 if solved but rejected (projection or tie).
- **C2:** composite's `(distanceToEye, transmission)`.
- **Also capture:** raw `depth0`/`depth1` (strict depth-format sampler), all from the same FINAL.
- **Byte-identical checks against baseline:** `depth1`, `depth0` outside status 0, and C1.

## Open gates (none passed by this unit)
- Actual hardware depth state during the water draw (DEPTH_TEST, FUNC, WRITEMASK). Prove it with a read-only `glGet`, or leave it open.
- Actual straddles in both directions, and the ceiling case. Report `null` if no Lab geometry falls in the band.
- Wave containment or headroom, i.e. contact physics.
- Later translucents, particles, hand and clouds interacting with the new depth.
- In-game evidence for the shadow-point move; for now it is checked only by source diff and native tests.
- The `:442`/`:408` source-radiance surface height.
- Coverage beyond the coarse mesh.
- Early-Z cost.
- Beyond this frozen setup (fixed phase, zero ripples, deep water, limited footprint): shallow, shore, cave and unknown worlds; R2; physical, visual and release acceptance.

Nothing here claims that all curl or visibility errors are solved.
