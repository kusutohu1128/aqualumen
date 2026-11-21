# Underwater near-wall reflection: next qualified regression slice

Codex static/source-and-artifact review, 2026-10-02. This is not a fresh Claude
Opus/Sonnet review, a shipping fix, a new GPU run, or visual acceptance. Only this
plan was written during the review. Root owns subsequent serialized GPU/runtime
work. The full realistic-water/sunlight goal remains open.

## Current evidence, with the qualification boundary retained

The original [native-default log](../../reports/2026-10-02-underwater-angular/native-default.log)
is **INCONCLUSIVE**, because its required positive reflected-wall control was
not resolved. It must not be renamed a shader RED merely because the near wall
looks mathematically visible. Its original inputs, original/passive outputs,
matrix packet and [source archive](../../reports/2026-10-02-underwater-angular/native-before-resolution-sources.tgz)
are frozen. Its angular subcheck is useful evidence, not a whole-test GREEN.

The fixed, input-only 0.55 m preset now provides a genuine resolved positive
control on the same production flat VS/FS:

- [Run](../../reports/2026-10-02-underwater-angular/native-wall055.log) and
  [serialized repeat](../../reports/2026-10-02-underwater-angular/native-wall055-repeat.log)
  both report NVIDIA RTX 3080 Ti, native GL 4.6, and terminal PASS.
- Input geometry selects pixel `18,16`: 1028 angle candidates, 100 independently
  four-corner-qualified candidates. The first input-qualified pixel is retained;
  no pixel is selected by C0, SSR success or tag response.
- At that pixel the saved positive C0 is `(0.18808098,0,0,1)`, the zero C0 is
  `(0,0,0,1)`, observed Fresnel is 1, and observed SSR path is `0.5507498 m`.
  The positive original C0 image and angular CSV are byte-identical on repeat.
- Original flat VS/FS are byte-identical between the 0.3 m and 0.55 m cases.
  The 0.55 m input change proves a live positive reflection chain; it does not
  establish exact physical radiance calibration or repair the 0.3 m case.

Read-only reconstruction of the frozen 0.3 m pixel `24,11` gives the following
[source-level seam](../../reports/2026-10-02-underwater-angular/underwater-angular-frozen-reflection-cpu-20261002.log):

| Quantity | Value |
| --- | --- |
| Independent first wall travel from observed biased start | 0.2999251994 m |
| Observed normal / Fresnel / SSR path | `(0,-0.99999994,0)` / 1 / -1 |
| First 0.4 m projected sample | `(0.13022650,0.01005006)` |
| Nearest source pixel / cell-boundary margin | `16,1` / 0.20078 pixel |
| Supplied depth32F / C4 red | 0.966195643 / 0.75 |
| Previous Z / coarse Z / reconstructed scene Z | -3.190000004 / -2.937282587 / -2.893581725 |
| Crossing-width residual | 0.043700862 m, below 0.4 m |
| `previous.z > scene.z - 0.25` signed margin | **-0.046418279 m** |

The fixed 0.25 m previous-depth policy is therefore the strongest falsifiable
candidate for this first-segment miss. The double CPU calculation is not a
GPU-internal trace replay. The saved C4/depth files are serialized supplied
inputs, not a separate post-upload texture readback. Those distinctions prevent
prematurely upgrading this observation to a fully qualified behavioral RED.

Alternative explanations to exclude are nearest-depth/source-footprint aliasing
and a projection/normal/bias mismatch. No claim is made that this native near-wall
case reproduces the user's natural underwater circle or dark exterior.

## ONE next public-original-main tracer bullet

Add one opt-in near-wall regression at the existing original
`gbuffers_water.vsh` / `gbuffers_water.fsh` main seam. Do not call or replace
`reflectionTrace` with a test implementation. Keep public `WAVE_HEIGHT=0`,
`SHORE_FOAM=0`, the frozen native 129-square projection, flat interface 3.25 m
above the eye, and the original 0.3 m closed wall. Freeze target `24,11` before
any C0 response. The 0.55 m case remains an independent positive control, not a
replacement for the near-wall regression.

Qualify the following **before evaluating the near-wall source gain**:

1. The actual bound samplers, active uniform types, dimensions and storage
   formats agree with the fixture. Read back actual uploaded C4 and depth input
   textures and require finite data, exact source masks and their declared
   RGBA32F/depth32F rounding. Pin source/program/matrix hashes and renderer.
2. Independently invert the supplied float matrices in double precision.
   Intersect the eye ray with the original rasterized flat interface and both
   the physical mirror ray and the explicit shader-biased ray with closed
   boxes. Require the same first wall side, no nearer occluder, underwater
   receiver height and a constant tagged source for both origins.
3. Qualify all four target pixel-corner rays and all four projected camera-source
   pixel-corner rays. Their complete source/visibility envelope must stay on
   that same wall side and away from a silhouette or a different palette.
   Include both texture-cell and matrix/storage error envelopes, rather than
   trusting one ideal center hit. Preserve the existing viewport thresholds.
4. Independently prove TIR with a resolved critical-angle margin for the full
   target footprint. Qualify the actual passive interface position/normal and
   Fresnel=1 against that geometry. Exclude refraction/proxy, foam, sky, direct
   Sun and scatter: zero source controls must be zero, and the actual incident
   field/cache quadrature inputs must be zero.
5. Run original zero/tag/repeat draws and removable final STORE-only observation
   draws. Removing stores must recover the original option-main byte-for-byte;
   whole-image C0 neutrality and repeat must hold. First establish the resolved
   0.55 m positive chain using the same actual binding/storage checks. A failure
   here is **INCONCLUSIVE**, not a new near-wall RED.

Use the frozen tag `D=(0.75,0,0)` only on the independently visible wall, zero
elsewhere. Read-back D, not the requested literal, is the source amplitude.
The near-wall branch must **not** require observed SSR path>0, positive C0 or
successful private tracer predicates to qualify: those are outputs under test.
Otherwise the exact failure would silently exclude itself.

## Independent positive-response and path oracle

The physical mirror/source/Beer expectation is positive. Retained SSR also
deliberately fades source near screen edges and uncertain depth, so demanding
the ideal `D * Beer(t)` amplitude would incorrectly reject its existing policy.
For this narrow regression declare a conservative nonzero lower bound:

`delta C0_red >= F_min * D_min * exp(-0.32 * t_max / WATER_CLARITY) * e_min * c_min - numericalBound`.

Derive every term from prequalified inputs, not successful SSR outputs:

- `F_min=1` follows independent TIR; `D_min` is the minimum actual source value
  over the whole qualified camera-sample footprint.
- Independent closed-box first intersection gives `t*`. The existing four
  refinement budget permits at most `0.4/16 = 0.025 m` first-segment ray-interval
  width, **provided** the independent sampled wall-depth envelope proves a
  sign-separated first-crossing corridor of the same wall: all admissible
  depth errors give the pre-hit sign before the corridor and the post-hit sign
  after it. NEAREST depth can jump between texels and need not be pointwise
  monotonic inside that corridor. Add camera-pixel depth variation, depth32F
  quantization and a declared float matrix/raster envelope. This gives `t_max`
  and the allowed returned-path interval. If this proof fails, report
  INCONCLUSIVE; do not assume bisection works across an occlusion edge or an
  unbounded raster-depth alias.
- Project that complete interval and error envelope independently. Its minimum
  screen-edge distance gives `e_min` under the retained public 0..0.08 edge-fade
  policy. Require the envelope to resolve a nonzero value.
- Derive a maximum view-Z residual from the independent plane/pixel/depth
  envelope, not a copied tracer loop. This gives `c_min` under the retained
  0.05..0.18 confidence policy for the first 0.4 m segment. If the envelope
  cannot give positive confidence, the test is not yet qualified.
- `numericalBound` includes actual input storage, binary32 source/Beer/Fresnel
  arithmetic and both C0 subtraction storage errors at the full common C0
  magnitude. Do not count only tag-sized ULPs or choose an arbitrary threshold
  from the observed zero. Require the derived source lower bound to exceed it
  by a predeclared resolved margin before evaluating the response.

This is an independently derived **lower bound**, not an exact reproduction of
the production edge/confidence algorithm or a general SSR radiometric theorem.
Observe the final `reflectedHit` RGB/path via passive stores. For a successful
near hit require a finite positive path within the independently bounded first
receiver interval, not merely any positive path or a later wall. Zero and
untagged G/B controls remain zero; alpha remains 1. Preserve whole-image C0
neutrality and repeat. A deliberately wrong no-reflection/F=0 expectation must
be rejected by the resolved 0.55 m positive control, excluding an insensitive
measurement/oracle.

Only after all input/control qualifications pass may current near-wall zero
gain, a missed path or a later/wrong receiver count as **behavioral RED**. Apply
any production fix after that RED, then require the same frozen near test GREEN,
the 0.55 m control and angular suite retained, plus existing false-edge,
foreground/sky/underwater/above-water compatibility cases. A more permissive
previous-depth window must not admit an arbitrary background surface simply
because its depth lies within a wider range.

## Applicability and source identity

The captured 1600x900 four-matrix FOV cannot accommodate this deep fixture's
on-screen reflected-wall control. CPU densities 129x73, 257x145 and 513x289 all
fail the unchanged initial march/receiver viewport qualification. This is an
applicability limit, **not** a demonstrated cause of the user's image, and no
FOV manipulation or partial angular GREEN is promoted to natural-scene repair.
The circular Snell window can be physically legitimate; offscreen occlusion,
wave-rim appearance and actual Minecraft GL3.2 remain separate runtime work.

Current source hashes verified read-only:

- Water VS: `ad5f0ad33bdc9df04f5c6d0a18bbd87fd1f16442a2b46d836ea79a481451e219`
- Water FS: `c8cdbde6bc15fbf7dab3b59efd6f2897202eb2d5a1c0aee6bf71890b5f7e4ced`
- Water coefficients: `e9e6ac73ca6c451907e8f515913898b000e494c55947cd5e2f44d05db3d65b39`
- Current angular header: `84fc58df700f8fb9a961046623ec24b0711eeb622724f73babbeb22ef4315a98`
- Both frozen original flat FS: `9596acc2349fbe891032433a39850ef310e4ca801349f3e13fc0400b4e6a5486`
- Both 0.55 m angular CSV: `44bd739a7d0d08a4cdc16a5e17177ae99f2882ba925f485f4de14db61fc2c1e6`

This specification is the next goal slice. No near-wall shader fix or actual
natural underwater acceptance has been completed by writing it.
