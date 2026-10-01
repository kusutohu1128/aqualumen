# Stepped-shore diagnostic design after the bounded 0.5 transport slice

Status: design only, 2026-10-02. No C++/shader changes, GPU execution, game
commands, configuration changes or new RED/GREEN claim accompany this document.
The live game being paused does not authorize native GPU work. Root must grant
an exclusive slot and authorize each diagnostic override before execution.

## Evidence and the seam that the existing test does not cover

The inspected 0.4 `after/coast-day.png` contains broad cyan bottom windows and
dark, serrated reflected bands; `after/river-day.png` also contains sharp bands
over real block-shaped shore geometry. They are not captures of the current
0.5 code. Neither still identifies a specific failing ray or separates reflected
sky/bank radiance from transmitted bottom radiance.

`tools/glcheck.cpp::shoreContinuityProbe()` (lines 861–963 at inspection) is a
valuable actual-main test: a smooth horizontal bed changes physical depth under
fixed-phase, tessellated water, using linear-filtered analytic depth and smooth
world-Z albedo. Its original tiny-depth bracket is retained explicitly. It does
not contain a bank riser, an above-water SSR target, or an opaque silhouette;
passing it does not prove continuity at a discrete source/visibility boundary.

Current production source has three relevant couplings:

- `gbuffers_water.fsh:173,181–204`: original camera-ray depth controls fragment
  slopes and unresolved roughness. The normal then drives Fresnel and both rays
  (`207–209,263`). Vertex displacement instead uses the depth-64 spectrum
  (`gbuffers_water.vsh:26`, `waves.glsl:62–65`).
- `gbuffers_water.fsh:24–73,266–269`: SSR chooses an opaque C4 receiver or a
  filtered directional environment. Edge/residual weighting does not prove
  continuity at every earlier march sample or geometry silhouette. The
  `surfaceY-0.30` exclusion still admits a legitimately shallow receiver within
  30 cm of the surface; whether a sampled source is physically reachable needs
  world geometry, not just the final receiver height.
- `gbuffers_water.fsh:232–261`: the above-water refracted hit is validated and
  confidence-blended with an independently attenuated original-UV proxy. The
  new incoming Sun correction is applied to the confirmed hit, not the proxy.
  A first zero-Sun diagnostic avoids conflating that bounded transport choice
  with the older visible-band question. No bank guard should be relaxed.

## Ranked one-variable ablations and their predictions

Run each against the same unmodified production vertex/fragment baseline,
geometry, frozen phase, textures and projection; do not combine ablations.

1. **Optical normal → existing `geometricNormal`.** Highest-priority broad-band
   diagnostic because the observed bands extend beyond shallow taper depths,
   and one field jointly controls reflection/transmission directions and
   Fresnel. A root-produced override assigns `n=geometricNormal` immediately
   before `normalView`/derivatives. Keep the vertex program, wave displacement,
   spectrum variance and every trace/transport operation unchanged. If bands
   collapse but bottom/SSR source controls survive, angular shading is involved.
   If source boundaries survive almost unchanged, this loses priority. This is
   intentionally a broad test, not an attribution of the change solely to SSR.
   The existing `geometricNormal` is the supplied Minecraft face normal, not
   the true normal of the displaced/tessellated triangle; label it accordingly.
2. **SSR → environment only, refraction unchanged.** Most surgical source-switch
   diagnostic. Root changes only the reflected-hit selection to the existing
   `environment` with no hit distance; all refraction, normals, Fresnel, sky
   convolution and specular stay identical. Above-water reflection-tag response
   must disappear, while an isolated bottom-colour control remains responsive.
   If the jagged boundary co-locates with reflection-tag response and disappears
   here, SSR-source selection is implicated. Persistence rules out SSR as the
   sole cause; it does not rule out Fresnel mixing of sky and bottom.
3. **Fragment wave depth → 64 m, geometry unchanged.** Root changes only the
   depth argument of `waveStateFiltered`; vertex displacement, initial Snell
   depth/path, caustics, foam depth and rejection guards remain untouched.
   The shore multiplier is unity above 0.8 m (`waves.glsl:56–59`), so this must
   not alter pixels whose original receiver depth remains safely above 0.8 m.
   A response restricted to shallower pixels supports the view-depth/normal
   feedback hypothesis. Broad deep-water changes instead invalidate the
   isolation or depth classification. This cannot repair true block silhouettes.
4. **Competing non-ablation explanation:** real bathymetry/albedo/occlusion
   discontinuities plus the selected RGB extinction and sky contrast. If all
   three controls retain a boundary aligned with a physical receiver edge,
   avoid calling it a solver seam. Incoming Beer preferentially removes red;
   the 0.5 energy fix is not a promise of lower cyan chromaticity.

These are root-owned, explicitly labelled diagnostic versions of production
main, not a copied/reimplemented tracer or a shipping shader change. Hash the
baseline and each narrowly different expanded program. No diagnostic helper
output or private receiver-kind rule is used as the pass/fail oracle.

## Reproducible fixture inputs

Use the real `gbuffers_water.vsh/fsh`, material attribute `mc_Entity.x=10000`,
RGBA32F output, matching full-size C4/C8/depth snapshots and a distinct output
texture. Start with 129×129 output/input grids, FOV 60°, near 0.1 m, far 128 m,
identity camera view/inverse, eye at camera-relative `(0,0,0)`, absolute
`cameraPosition=(0,62,0)`. Mean water plane is `y=-0.5`; draw the same one-metre
quad tessellation over `x=[-8,8]`, `z=[-24,0]` for every baseline/variant.
Use public WAVE_HEIGHT=0.12, WATER_CLARITY=1, WATER_ROUGHNESS=0.075 and
SHORE_FOAM=0 initially: foam-off is a common legal fixture setting, not one of
the three ablations. Pin `frameTimeCounter=1.25`, dimension 0, eye-water 0,
lightmap `(0,1)`, white vertex colour/texture, supplied normal `(0,1,0)`;
`aqualumenActive=0` disables interaction ripples. Keep rain/wetness zero.

Generate a **closed** world-space voxel-bank heightfield, not a hand-painted
depth stripe. For horizontal cells within the fixture, let
`B(z)=b+floor((-z-2)/4)` and top height be:

- `x < B(z)`: deep bed `y=-1.75` (1.25 m below mean water);
- `B(z) <= x < B(z)+1`: one-metre-wide shallow ledge `y=-0.75` (0.25 m below);
- `x >= B(z)+1`: dry bank `y=0.25`.

Include the vertical risers, stair corners and side/end faces, with solid bottoms
at `y=-4`. For each input texel, independently intersect its camera ray with
these faces and retain the nearest positive visible intersection within far.
Project that hit to perspective depth; assign its C4 radiance and matching C8
from the same face identity. Empty rays have depth 1 and sky background. This
is independent scene ray casting, not an oracle for the shader's march steps.

All submerged surfaces initially have constant neutral C4 `(0.25,0.25,0.25)`;
dry bank has `(0.12,0.10,0.08)`. The first source-switch experiment uses C8=0
everywhere, zero direct-Sun cache, upward Sun direction `(0,1,0)` held fixed,
and a 64×32 constant neutral sky LUT `(0.04,0.04,0.04)` excluding its reserved
last row. This cancels Sun-caustic/specular source complications without deleting
diffuse environment or actual receiver radiance. A genuine brighter bottom
control changes total C4 locally, not only its attribution texture.

Depth-test water against a **separate**, identically seeded opaque depth
attachment, with depth writes disabled. Never sample the framebuffer's attached
depth texture: the sampled `depthtex1` is another allocation. Dry-bank pixels
must occlude water rather than receiving a water overlay. C4, C8 and sampled
depth must likewise be distinct from the colour output. First use NEAREST depth
and radiance, then rerun LINEAR as a separate filter experiment; interpolating
depth across a riser creates a nonphysical intermediate receiver and cannot be
silently treated as a ground-truth continuous scene.

## Public-output source switch and perturbation loop

Place a distinct reflection target at world `z=-6`, `x=[-2,2]`, `y=[0,1.5]`:
the visible front of a closed thin opaque box. It is fully above the water.
Pair its total C4 radiance between `(0.08,0.08,0.08)` and `(0.45,0.08,0.08)`;
C8 stays black because this controlled radiance is not direct Sun. Re-raycast
the same geometry; no target depth or other face illumination changes in the
pair. A mean-plane geometric-normal reflection from near pixel `(64,40)` reaches
this target; the original camera ray and downward transmitted ray reach the
bed. Its projection lies above the camera horizon, outside those original-UV
water pixels. Verify this world-placement condition for every retained ROI
pixel, not merely by naming the object a reflection tag.

Record the complete raw HDR/alpha image, deterministic repeat error, and the
paired tag response `Rtag = output(bright target)-output(neutral target)` for
baseline and each ablation. Do the analogous pair for a green-colour increment
on a visible submerged receiver, keeping all other faces and C8 fixed. This
preserves nonvacuous transmitted-geometry and reflected-hit controls. With C8
black, there is no fixed-total attribution ambiguity; later true Sun pairs
would have to change C4 total and C8 direct component coherently.

Translate only bank parameter `b` over `[-0.05,0.05]` m in 0.002 m increments,
reraycasting coherent snapshots while camera, water vertices and phase remain
fixed. Track the largest finite HDR change and the tag response on water-covered
ROI pixels; refine its original two endpoints by bisection up to eight times.
Save the original bracket as well as any adaptive maximum. Report stable
source-response regions versus genuine camera/receiver/occlusion edges. Only
after this frozen loop is informative, consider a separate wave-phase sweep;
do not vary phase and bank displacement in the same experiment.

Falsifiable outcomes, without an invented aesthetic threshold:

- The SSR-environment override must have zero reflection-tag response within
  finite/repeat-error tolerance on independently qualified water ROI pixels;
  a valid baseline reflected-hit control must be nonzero. If the tag overlaps
  the original/proxy/transmitted receiver, exclude that pixel rather than call
  its response leakage. Source tags must not suppress a legitimate reflection.
- The real bottom-colour response remains nonzero in every variant that still
  has a visible bed. Removing both source responses is a vacuous diagnostic.
- Depth-64 must leave safely-deep ROI output unchanged within repeat/float error,
  but may alter shallow normal-driven bands. Geometric-normal ablation is not
  expected to preserve ray maps or make the scene physically correct.
- A vanishing-input/finite-output jump is a candidate defect only where actual
  receiver identity, radiance and visibility stay continuous. A stair edge,
  bank occlusion, mirror-source edge or a NEAREST texel switch can legitimately
  remain sharp. Preserve foreground rejection even when it creates a miss.

## Limits and next decision

No run is claimed, so no failing stepped-bank bracket is currently known.
This design deliberately does not promise a RED or normalize every serration
into a bug. The smooth-bed legacy GREEN remains narrower evidence; late-iterate
bank rejection and arbitrary silhouettes remain unverified.

Native colour/source response can discriminate paths, not establish the precise
cause of a natural screenshot. Minecraft has textured slopes, foliage, shadows,
moving clouds and a different raster scale. The fixed neutral LUT and simplified
closed bank omit those sources. Any implicated path needs a later same-camera,
same-phase natural validation under a separately authorized runtime session.
No tint change, solver relaxation, spectrum rewrite or release selection follows
from this document alone.

## Executed diagnostic: post-0.5 evidence, not a new release fix

The design-only history above is retained. Root subsequently authorized the
opt-in `tools/glcheck.cpp::shoreDiagnosticProbe()` and the three exact fragment
ablations, against frozen commit `4d732c9` / ZIP `88ff…`. Shipping GLSL, options,
worlds, configuration and the default acceptance-test calls were not changed.
`--shore-diagnostic-only` is deliberately **not** part of `make check`.

Executed from `/home/kusutohu/repos/aqualumen`:

```sh
make build/glcheck
build/glcheck shaders --shore-diagnostic-only > build/shore-v0.5-diagnostic/diagnostic.log 2>&1
```

Both runs exited 0 on `NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2`, OpenGL
`4.6.0 NVIDIA 580.173.02`. Root granted the exclusive native diagnostic slot
while Minecraft was paused and no Minecraft frame measurement was running.
This is not a Minecraft FPS result. GPU access was released after the second
run; no further native jobs are implied by this document.

The initial complete directory is preserved, without overwriting its generated
files, as `build/shore-v0.5-diagnostic-first/`. The qualified second run is in
`build/shore-v0.5-diagnostic/`: raw 129×129 bottom-up float32 RGBA dumps, raw
HDR RGB PFM images, source-response CSVs, `inputs.csv`, `endpoint-inputs.csv`,
`jumps.csv`, `same-baseline-bracket.csv` and the expanded programs. Each original
coarse bracket and its separately refined endpoints is saved. The scene clamps
the near-eye floor to `B(z)=b+max(0,floor((-z-2)/4))`; this keeps the camera
outside the dry solid. This is the recorded adjustment to the initial design.

SHA-256 of executed expanded source (common legal SHORE_FOAM=0 baseline; the
vertex text is unchanged for all four programs):

| Artifact | SHA-256 |
| --- | --- |
| production-unchanged.vsh | `6d2406e9fe5c7be418ef063bfd8633a05385858c283bf2cfae6c238926e8d6cd` |
| baseline.fsh | `d8c8ad0d2f4a56d52d0829f94c3dccb1c183fa5cd0c2a6da86fdde49b5e55303` |
| face-normal.fsh | `4465b78056ed30301b5bfc2fbb8293781461f0ab0530f8ed469bfb981d1bf931` |
| environment-only.fsh | `0ed8b7f18d31ea5d4825cd4556556f3716d7769e5738d5e833d36f2c34d87e9b` |
| fragment-depth64.fsh | `72b12d73c09b8d11ed60cadbd3b3376f26173b1a59428c12b2b8344c67025954` |

The preserved first log hashes to
`39397cbcd0f30222a47b6c78f96a8cc3c9dddd3e888bf95e65fc4e048cf89f3c`;
the second to
`af0cd5226ec9765a1b13d7f134937be04a02aa0299cb2bfac4f316b3c4dbd3c4`.

### Source/geometry controls before perturbation

The water ROI is `x=20..108`, `y=10..56`, using lower-left framebuffer pixel
coordinates. It contains 3,945 water-covered pixels at b=0; retained comparison
pixels have alpha=1 in both renders. Their original camera rays are below the
horizon, whereas the reflection target is fully above water and its camera
projection is above the horizon. Geometry and sampled inputs use separate
depth allocations; no sampled attachment feedback is present.

Filter-specific controls were actually executed for **both** NEAREST and
LINEAR. All four variants had deterministic-repeat RGB error 0 and positive
deep-receiver response. Baseline red reflection-tag maximum was 0.150754 with
NEAREST and 0.145343 with LINEAR; environment-only response was exactly 0 with
both. Baseline deep and shallow green response maxima were respectively
0.142165 and 0.160169. These are source-response amplitudes, not a visual score.

Equal green maxima alone would not separate paths. The second run computed
pointwise `(tagged-baseline − baseline) − (tagged-environment-only − environment-only)`
for each submerged source. Its NEAREST magnitude was at most `2.98023e-08` for
both deep and shallow tags, at `(41,16)` / original face172, part0, y=-1.75 and
`(106,18)` / face202, part1, y=-0.75 respectively. Thus submerged-source SSR
was **not demonstrated in this fixture/phase**, despite the source cutoff
making shallow receivers eligible. This is not proof that it cannot happen.

An additional depth-writing render of the real unchanged vertex program,
against an independently seeded clear depth attachment, measured displaced
water Y. Deep-64 qualification required the full derivative quad to have a
real deep original receiver and measured water-to-receiver clearance >0.85 m.
2,064 pixels qualified; minimum measured clearance was 1.13674 m and maximum
baseline/depth64 RGB difference was exactly 0. This confirms isolation well
above the 0.8 m taper cutoff without equating RMS wave height to peak amplitude.

### Initial largest jumps were input discontinuities

The first baseline maximum was at `(23,55)`, coarse b=0.026..0.028 m.
Refinement to b=0.0277734362..0.02778125 m retained RGB change 0.121348321,
but original input changed face19→no receiver and C4 `(0.25,0.25,0.25)`→sky
`(0.04,0.04,0.04)` at the finite outer field. It is **not** evidence of a solver
continuity defect; no SSR reflection-tag response accompanied it.

The face-normal variant's initial same-face maximum at `(108,42)`, coarse
b=0..0.002 m, likewise cannot be a continuity oracle. Face195 remained the
same, but original y crossed the fixture's sharp wet/dry palette threshold,
-0.5→-0.500003934 m. C4 changed from `(0.12,0.10,0.08)` to gray `(0.25,0.25,0.25)`.
This explains why same original face/part alone was insufficient qualification.
The first outputs were preserved rather than presenting these as a RED.

### Qualified scan and exact same-bracket ablation comparisons

The second scan retained raw measurements and separately required original
face/part identity, unchanged original C4 and alpha=1 for the **entire** endpoint
derivative quad. LINEAR additionally padded that quad to a 4×4 source footprint.
Empty/tag original receivers, outer world side edges and changing palettes were
excluded. There were 191,250 eligible endpoint-pixel pairs over 50 NEAREST steps
and 180,990 LINEAR pairs. This does **not** certify the shader's refracted/SSR
receiver identity, nor stability of a NEAREST sampled texel.

The baseline's qualified NEAREST maximum was at `(65,46)`, coarse
b=0.0460000001..0.0480000041 m, RGB change 0.0514032841. Its fixed-pixel bracket
refined to b=0.0464765616..0.0464843735 m (7.81193e-06 m), retaining 0.051877059.
Original face165 / part1, C4 gray and alpha=1 stayed fixed throughout the
qualified quad. At the selected pixel original y varied continuously from
-0.836578131 to -0.836718738 m; reflection-tag response was 0 at both endpoints.

The **same baseline pixel and fine endpoints**, not each variant's independently
chosen maximum, gave:

| Filter and fixed baseline bracket | baseline | face normal | environment only | fragment depth64 |
| --- | ---: | ---: | ---: | ---: |
| NEAREST, `(65,46)`, 0.04647656..0.04648437 m | 0.0518771 | 9.56655e-06 | 0.0518771 | 7.45058e-09 |
| LINEAR, `(65,46)`, 0.04844531..0.04845313 m | 0.00166225 | 5.23329e-05 | 0.00166225 | 3.30806e-06 |

The qualified LINEAR original coarse bracket was b=0.0480000041..0.0500000007 m,
RGB change 0.035251081. Its reduction after refinement is different from the
NEAREST result; an eight-refinement sample is not an asymptotic proof. Original
face165/C4/alpha remained stable, with y=-0.872015655..-0.872156322 m.

Every variant still found other switches when allowed to choose its own maximum.
For example fragment-depth64's qualified fine jumps were 0.0495198 with NEAREST
and 0.0716468 with LINEAR, at other pixels/brackets. Disabling one field therefore
does not justify calling all shore boundaries fixed. Their endpoint metadata
and raw images are retained in the same artifacts directory.

### Bounded conclusion

The observed **particular** qualified baseline source switch is sensitive to
optical-normal/fragment-depth coupling and unchanged by environment-only SSR.
That falsifies SSR-source selection as the sole explanation for that bracket.
It does not establish that a natural cyan boundary has the same cause or that
deep64/face-normal is a physically correct shipping solution.

Screen-space candidate identities, depth texel boundaries, true stepped/riser
visibility and earlier-iterate rejection remain possible explanations for the
finite difference. The bank scan demonstrates a useful deterministic feedback
loop, not a new behavioral RED requiring unconditional smoothing. Preserve the
0.5 shader freeze and existing rejection guards until a further separately
authorized test distinguishes such a defect from legitimate/input transitions.
