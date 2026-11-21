I did 6 reads: `gbuffers_textured.fsh`, `lib/terrain.fsh.glsl`, two reads of `tools/water_depth_candidate.py`, a grep of `shaders.properties`, and a glob of the `gbuffers_*` files. I wrote nothing, and that includes the plan file, because you said no writes.

## Who writes what, and data shape

- **C0 and C5:** `gbuffers_textured.fsh:5` and `lib/terrain.fsh.glsl:10` both declare `DRAWBUFFERS:05`. The terrain include is also used by terrain, textured_lit, entities, hand, particles and weather.
- **C12 and C3:** only water writes these. C3 is `(opticalPoint, projectedDepth | -1 | -2)` (`water_depth_candidate.py:62-63`).
- **C2:** composite overwrites it with distance and Beer transmission (`:73-74`).
- **Depth:** `depthtex1` is the depth before translucents. So `depth1=1` with `depth0` closer than water means a translucent-phase draw that ran after water won that pixel. Square components fit camera-facing particle sprites, but that is still inference. Your requirement for a witness stands.
- **Blend:** the only blend key is `blend.gbuffers_water=SRC_ALPHA ONE_MINUS_SRC_ALPHA ONE ONE_MINUS_SRC_ALPHA` (`shaders.properties:17`). It applies to every water output, C3 included. That means C3.w (the depth) acts as source alpha. Before relying on exact C3 values, confirm that the generated pack overrides this per buffer. I couldn't check it within the read budget.

## Choice: A is safe, with conditions

A records who last wrote each pixel. B classifies pixels using the depth it is supposed to be testing, which is circular. B also needs a channel that doesn't exist (C3.w is taken), and it can't name an owner. With alpha-blended draws that don't write depth, a depth token can't separate "touched" from "changed". I'd reject B.

Under A, a final −3 means the last fragment to survive discard at that pixel came from a nonwater program. Call it `lastWriterNonwater`, not "later". The terrain include also runs for opaque terrain, which draws before water. Wherever water later wins, it overwrites the marker, so last writer is the right meaning.

## Specific risks

1. **Blend can make the marker disappear.** Translucent passes (particles, clouds, weather) use Iris default alpha blend. Writing `C12=vec4(0)` with alpha 0 leaves the stale value in place. Writing C3.w=−3 with alpha 0.5 produces a mixed value. You need `blend.<program>.colortex12=off` and `.colortex3=off`. With Iris fallbacks (particles/entities/hand/weather → textured_lit; clouds/beacon/spidereyes/glint/skytextured → textured), it's unclear whether those keys bind to the fallback source name or to the original program ID. Witness this natively; don't assume it.
2. **Coverage loss.** A pixel with a depth-mask-false particle over a genuinely wrong water depth gets marked, and its water record is erased. That would hide a real failure. Fix: baseline3/candidate3 come from pinned run-2 packs, the scene is frozen, and the water bytes are identical, so join run 3 against run 2 per pixel:
   - Every marked pixel must have `depth0_3` strictly closer than run 2's projected water depth.
   - Otherwise it counts as a failure.
3. **Extra −3 pixels.** Terrain, sun/moon (skytextured → textured) and clouds now leave −3 where C3 used to be cleared to 0. Declare this in the protocol and update any C3 readers that treat w==0 as "none".
4. **Unlisted paths.** `gbuffers_basic` (block outline, leash, lines) draws after translucents. Either patch it or list it as unmarked in `programList`. Leave `skybasic` alone. Ice and stained glass go through `gbuffers_water`, so they still produce water records.
5. **Discard order.** The marker must be written after `discard`, so cut-out texels keep the water record.
6. **Output formats.** Confirm C12 and C3 formats accept exact 0 and −3 (C3 should be float).

## Minimal contracts

- Patch only C12 and C3 outputs: `RENDERTARGETS:0,5,12,3` with `C12=vec4(0)` and `C3=vec4(0,0,0,-3)`.
- Assert C0, C5 and the depth expressions are byte-identical to before.
- Water, VS, composite, physics and control ZIPs stay byte-identical. Verify this from the pack hash table in the receipt.
- New versions are hit1d3/depth3, with a new output directory (`exist_ok=False`, as now), so the 445 report is untouched.
- Record in the manifest: `markerProtocol`, `programList` (patched, fallback-covered, explicitly unmarked), `laterNonwaterMarker:-3`, and blend keys.

## Tests

**Native, fail-first:** draw a water quad, then a particle quad over it, and run 6 checks:
1. **Before the patch:** C12 and C3 equal the water values (stale). This must fail the ownership assertion.
2. **After the patch:** C12 is exactly 0 and C3 is bit-exactly (0,0,0,−3).
3. **Passivity:** C0 and depth are bit-identical to the unpatched run at alpha 0.5, with depth mask true and depth mask false.
4. **Blend-on negative control:** C12 stays stale or mixed, which proves the off key is what does the work.
5. **Discard:** a texel with alpha < 0.1 keeps the water record.
6. **Water after a particle with depth mask false:** water takes the pixel back.

**Actual deep run:**
- Report the marker count and connected components.
- All 445 failing pixels must be marked.
- Unmarked mismatches must be zero, against the same 1 mm budget.
- Every marked pixel must pass the run-2 join (strictly closer).
- Every unmarked pixel's `depth0` must be bitwise equal to run 2.

Passing these shows who owns each pixel and nothing more. Visibility, particle physics and visual acceptance remain separate gates.
