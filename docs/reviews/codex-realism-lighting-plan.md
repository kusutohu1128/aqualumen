# Codex realism lighting plan

Static source and saved-image review, 2026-10-02. This is a Codex review, not a
new Claude Opus/Sonnet review. No shader/test changes, model calls, GPU tests,
Minecraft operations or fresh frame measurements were performed for this
review. The only authored artifact is this document. Proposed work below is
**not implemented or accepted by this review**.

The [persistent realism goal](../REALISM_GOAL.md) remains active. The delivered
0.3.3 pack is the visual baseline; the working tree also contains the root's
in-progress Sun-only MRT change. Finishing the shore-water slice, this plan, or
one cloud improvement does not complete the full water-and-sunlight goal.

## Evidence and priorities

Saved 0.3.3 [day](../../reports/2026-10-02-v0.3.3/compatibility/ocean-day.png),
[dusk](../../reports/2026-10-02-v0.3.3/compatibility/ocean-dusk.png),
[night](../../reports/2026-10-02-v0.3.3/compatibility/ocean-night.png) and
[rain](../../reports/2026-10-02-v0.3.3/compatibility/ocean-rain.png) captures were
inspected. The cloud contours are smoother than the old coarse sky lookup, but
day/rain show a broadly continuous patterned layer rather than varied, distinct
cloud formations. Dusk has useful warm horizon/reflection separation. These are
stored observations, not captures of the new Sun MRT, and cannot establish
motion stability, cloud-shadow alignment or a new performance result.

1. **Spatial direct-Sun coherence:** `prepare.fsh` caches atmospheric and cloud
   transmission along the camera's solar column in C6. Terrain, water and local
   air consume that same value. `cloudSolarTransmission` has no receiver-world
   argument. Consequently a camera changing cloud columns can change direct
   illumination across the whole view; the model cannot produce the matching
   local patches of cloud shade on land/water. This is confirmed from source,
   not a measured explanation of every visible defect.
2. **Emitter radiometry/HDR:** `SOLAR` is used as direct-beam irradiance, while
   `sunDisk` emits `SOLAR * transmission * 20`. Its solid angle is much too small
   for those quantities to represent the same emitter. See the bounded
   calibration proposal below; simply raising that constant is unsafe.
3. **Cloud shape and source illumination:** the three-octave density, one layer
   envelope and coverage field can be diversified after light-path coherence.
   In `addCloudLayer`, the forward background `sky * 0.30` also becomes a local
   cloud ambient source. Angular incoming illumination and boundary radiance
   should be separate. Averaging noise toward 0.5 before a nonlinear density
   threshold may bias coverage/optical thickness; this is a plausible filtering
   issue, not a proven sole cause of the cloud carpet.

The current 32 view / 6 light steps, 750 m curved layer and Beer-Lambert segment
transport are a useful original procedural foundation. They are not a weather
simulation, full cloud/atmosphere multiple-scattering solution, or proof of
photorealism. Do not start by adding unbounded noise samples or recolouring the
shore water to hide a receiver/path error.

## Sun MRT: inspected topology and limits

The installed pinned JAR is `iris-fabric-1.8.8+mc1.21.1.jar`, SHA-256
`b5ad39a6cb113ca0a1765f06689f9f4b29ccd0c81247de90b06c42f5da1092f5`.
Read-only `javap -c -p` inspection verified these implementation details:

- `PackRenderTargetDirectives` builds supported target indices 0 through 15.
- `RenderTargets.createColorFramebuffer` attaches the *requested texture* to
  consecutive GL attachment/output locations. Thus `RENDERTARGETS:0,4,8` maps
  `gl_FragData[0..2]` to those three textures; it does not require a physical
  `GL_COLOR_ATTACHMENT8` for the third output.
- `IrisRenderingPipeline.beginTranslucents` copies pre-translucent depth, runs
  the deferred renderer, then enables blending. This supports the intended
  pairing of depth1, opaque RGB and opaque Sun snapshots.
- `RenderTarget` allocates both main/alt textures with the same internal format.
  For non-integer targets, `setupTexture` uses min/mag `GL_LINEAR` (9729) and
  `GL_CLAMP_TO_EDGE` (33071). An RGBA32F candidate follows the same filter/flip
  path. Native probes using only nearest sampling do not exercise all real-Iris
  interpolation cases.

The official [color-target reference](https://shaders.properties/current/reference/buffers/colortex/)
also describes valid indices, per-frame clearing and ping-pong targets. The
[deferred reference](https://shaders.properties/current/reference/programs/deferred/)
says most opaque geometry precedes deferred and most translucency follows it;
that qualification matters. The current source writes every declared deferred
output on every branch, declares C5/C8 RGBA16F, leaves them at display resolution,
and does not attach C8 while water reads it. No static topology blocker was found.

| Target | Current meaning and ownership |
| --- | --- |
| C0 | Current colour, including later translucent rendering |
| C4 | Deferred immutable opaque RGB/environment snapshot |
| C5 | Mutable direct-Sun surface contribution before deferred |
| C8 | Deferred immutable direct-Sun snapshot paired with depth1/C4 |
| C6 | Cloud-bearing sky radiance; final-row cache includes camera cloud attenuation |
| C7 | Cloud-free sky radiance; final-row cache is clear atmospheric solar transmission |
| C9+ / custom image | Candidate allocation for a future spatial cloud-transmission map |

`terrainLight` exports `albedo * directSun / PI` before adding Moon, diffuse sky,
block light or dimension ambient. It already includes that receiver's normal,
shadow visibility, skylight gate and weather factor. This is the correct
component to refocus in the present approximate receiver model. It is still
dry-lit terrain: the incident Sun's surface-to-bottom water leg has not been
solved, so the decomposition alone does not correct underwater irradiance.

Remaining acceptance risks:

- The initial source snapshot accepted a depth-valid original-UV proxy for
  above-water caustics. The subsequent source-progress addendum below confirms
  that the caller now requires `receiverKind == 1`; do not report that initial
  missing gate as a current defect. Offscreen/filtered receiver limitations and
  final runtime acceptance remain distinct from that correction.
- C5 writes alpha 1 while C0 may use texture alpha. If a partially blended
  surface occurs before deferred, these are not necessarily a matched linear
  colour decomposition. Zeroing an unlit layer is conservative for focusing,
  but can also erase a behind-layer Sun contribution. Do not claim all
  translucent compositions exact from the native fullscreen MRT test.
- Check actual Iris entity/block-entity/particle/fallback routes, cutouts and
  overlapping glass. A nearer opaque shader that fails to replace C5 could
  retain a farther surface's Sun. Post-deferred C5 writes cannot themselves
  change C8, but shader routing and draw order still require game controls.
- Defaults clear C5/C8 each frame; test first frame, resize, dimension changes,
  empty sky and pack reload. Do not rely on prior-frame contents. These runtime
  checks have not been run by this reviewer.
- Arbitrary refracted UVs interpolate C4/C8 RGB while depth classification may
  select one surface. At a silhouette or shadow boundary, a bilinear Sun
  component can include a neighbouring lit receiver. Matching C4/C8 filters
  keeps their colour decomposition consistent but does not prove a single
  geometric receiver. Include actual linear-filter cases in provenance tests.

## Minimal underwater caustic correction

At this snapshot, `composite.fsh` multiplies the entire current C0 colour by a
focus factor using depth0. This can focus diffuse/Moon/block light, water's own
scatter and a rendered interface's reflected/transmitted sky. A generic upward
normal shadow test does not establish the actual visible receiver's Sun path.

Recommended bounded change, independently red/green tested before installation:

1. Read opaque depth1 and C8 at the same pixel. Compute the receiver and its
   caustic footprint from depth1, with derivatives before divergent branches.
   Require Earth, active local water surface, valid opaque depth and the existing
   bounded receiver-below-surface/Sun conditions.
2. Only modify a visible receiver known to belong to that opaque snapshot.
   A depth0/depth1 mismatch proves a nearer layer and must skip this composite
   caustic; never use the deeper C8 component as though it belongs to a nearer
   water interface, glass or particle. Reject invalid/sky depths before
   unprojection. The pinned-depth addendum below supports **exact same-texel
   depth equality**, superseding the initial idea of a reconstructed-depth
   tolerance. A broad normalized-depth or world-distance epsilon can admit a
   nearer layer that was not in the opaque snapshot.
3. Apply `C' = C + strength * (focus - 1) * S`, where `S` is the nonnegative
   receiver Sun contribution from C8. Then apply the existing view-leg water
   transmission/scatter once. Leave other light components unchanged. Do not
   multiply C8 by a second upward-normal shadow/sky/weather factor: those gates
   already belong to its receiver illumination.
4. Depth agreement alone cannot identify a depth-write-disabled translucent
   layer. For the minimal slice, conservatively skip RGB that is demonstrably
   changed from C4; RGB agreement is an additional rejection check, not proof
   of opaque material identity. A complete solution would propagate an explicit
   visible direct-Sun component through each compositing layer or a reliable
   material/provenance mask. Until that exists, document and test this limit.

This correction intentionally does not refocus the opaque bottom through a
translucent interface in composite: that belongs to the interface's receiver
transport. It also does not implement a Sun photon map, refracted shadow map,
submerged-normal G-buffer, or incident water-leg attenuation. The current
`waterCaustic` uses a horizontal receiver-plane Jacobian and bounded finite-source
regularization; applying it to vertical walls remains approximate. Brightening
must not be interpreted as a complete physical bottom-light solver.

Independent production-composite checks (proposed, not run here):

- With C8 zero and a non-neutral wave/focus field, changing wave phase must not
  change opaque Moon/block/diffuse RGB. The old whole-colour multiply should
  fail this control.
- With a nonzero synthetic C8 component and fixed geometry, the RGB change must
  be parallel to that component: equal `deltaRGB / SunRGB` where nonzero, and
  zero change in channels with zero Sun. Add arbitrary ambient RGB while C8
  stays fixed; the absolute caustic delta must stay unchanged. This checks
  component isolation without duplicating the production focusing formula.
- Hold C8/depth1 fixed and move depth0 in front: caustic delta must become zero.
  Include sky, underwater-looking-up interface, glass, particle, depth-write-off
  colour change, strict cave/Sun-zero and non-Earth controls. A positive matched
  opaque receiver must still show the isolated Sun effect.
- For nonzero eye-to-receiver distance, the output delta is the pre-water
  Sun-only delta times the independently expected Beer transmission; the
  scatter term stays identical. Use actual production main with raw HDR output,
  not a copied tracer or a final display transform that could conceal leakage.

## Next vertical slice: world-coherent cloud shade

After the shore/provenance and Sun-isolation slice is accepted, implement a
bounded, world-anchored direct-Sun cloud transmittance field using the existing
original cloud density. This is the highest-value next light-coherence slice,
not a thermodynamic weather or GI expansion.

Separate the clear atmospheric cache (C7) from receiver-local cloud transmission:

`direct(receiver) = SOLAR * T_air * T_cloud(receiver) * scene_visibility`

Terrain's Sun component, water's direct incident/specular illumination and air's
direct source should query the corresponding receiver/volume point. Do not
multiply diffuse sky, Moon or block light by a Sun-only cloud mask. Do not
multiply a new `T_cloud` into the existing C6 solar cache: it already contains
camera-cloud attenuation and would double-count it. Keep C6 for the camera's
sky/reflection environment while making that approximation explicit.

Cache a modest local map once per frame rather than adding a full cloud march
to every terrain/water pixel. A 256-square starting map is a design candidate,
not measured cost/headroom. Keep C5/C8 reserved for the Sun decomposition; use
C9+ or a separately declared custom image. Define stable world anchoring,
camera rebasing, borders, dimension resets and unknown coverage before coding.
Respect receiver altitude: a flat sea-level shadow map reused without height
correction shifts shadows incorrectly at low Sun. Bound low-elevation rays and
the cloud interval; avoid dividing by a nearly zero Sun elevation.

Proposed production tests and visible acceptance:

- Fix the camera solar cache and supply two world receivers with identical
  normals/albedo/ambient but spatial cloud transmission 0.2 versus 1. The actual
  terrain/water/air programs must distinguish their direct light. The old
  camera-global path is the expected red control.
- Constant cloud transmission reproduces its equivalent old single-column
  direct-light case; transmission 1 restores the clear-air source. With scene
  visibility zero, changing cloud transmission changes no direct light while
  fixed ambient remains. Verify finite values and transmission in [0,1],
  negative/large world coordinates, rebasing, height, low Sun and dimensions.
- Test map construction against a higher-sample integration of the actual
  procedural density at fixed world points; testing only a synthetic map does
  not validate production density/column integration.
- In guarded matched natural scenes, moving cloud patches shade the same world
  locations on coast/terrain/water and modulate highlights/caustics/direct
  shafts coherently. Moving the camera through a stationary cloud field must
  not cause a whole-view direct-light/exposure jump. Inspect map-edge continuity,
  day/dusk/rain and existing cave/underwater/dimension regressions in motion.
- Record original old/new images and a separate temporal run with exact pack
  identities. Measure actual Minecraft/NVIDIA timings separately from video
  encoding and native GPU probes. No arbitrary-world 60 FPS guarantee follows
  from existing warmed captures or a small map proposal.

## Follow-up slice: radiometric emitter and HDR calibration

Radiance and irradiance must not share a value without their angular measure.
For a uniform disc of angular radius `alpha`, normal irradiance is
`E = L * PI * sin(alpha)^2`; this is derived from the cosine-weighted radiance
integral described in [PBRT's radiometric integrals](https://www.pbr-book.org/3ed-2018/Color_and_Radiometry/Working_with_Radiometric_Integrals).
Using the current `alpha = 0.00465` and `L = 20 * SOLAR` gives approximately
`E = 0.001359 * SOLAR`, about 736 times below the direct-beam convention.
This numerical source mismatch is not evidence that it caused the cyan shore.

Do not just replace 20 with approximately 14721. The red channel would reach
about 265,000 in current units, above RGBA16F's largest finite value 65,504 in
C0/C4. Establish a common internal radiance/pre-exposure scale or deliberately
choose wider targets before calibrating the emitter. Audit water GGX peaks,
source discs, volume coefficients, Moon/block-light conventions and display
exposure together; avoid Inf/NaN that the final shoulder cannot repair.

The root's narrower candidate is **C0 and C4 RGBA32F**, keeping C5/C8 terrain
Sun components and C6/C7 atmospheric/cloud sky in RGBA16F, with the analytic
disc emitted only into the wider camera/opaque path. This is reasonable as a
separate, test-first slice: direct terrain radiance is much smaller than disc
radiance, and C6/C7 do not currently contain the analytic discs. Do not raise
the cache/sky formats indiscriminately. Verify actual peak values before
asserting the retained 16F targets safe under all settings.

The two wider targets each have main/alt textures. At 2560x1440, changing those
four allocations from 8 to 16 bytes/pixel adds 112.5 MiB of uncompressed base
texture storage, excluding other buffers/driver overhead. This is calculated
storage, not measured VRAM use or a predicted FPS result. Bandwidth and actual
Iris allocation/completeness need validation after the water slice is frozen.

Proposed tests integrate the actual production Sun-disc output over projected
solid angle with black environmental background, independently comparing to
its direct irradiance. Check angular resolution/FOV and antialiasing energy,
actual target-format finiteness, Lambertian `albedo * E / PI`, and matching
atmosphere/cloud attenuation. Preserve a single emitter in reflected/transmitted
paths; do not add an analytic Sun twice to a LUT that already contains it.

Suggested calibration order and independent controls:

1. Before production changes, render the **actual deferred pair** with all
   depth1 pixels set to sky, black C6 radiance except a unit solar cache, known
   projection and Sun fully inside the viewport. Read raw RGB, subtract the
   zero-cache control and integrate `L * dot(ray,Sun) * dOmega`. Use the camera
   projection's solid-angle Jacobian, not an unweighted pixel average or the
   shader's own normalization constant. A tightly framed, well-resolved disc
   with successively finer angular grids can expose the expected old 0.001359
   ratio without a copied implementation. Do not assume a 64-pixel disk-presence
   test establishes irradiance.
2. Add attachment-range controls without editing production: a known candidate
   disc-radiance value written to separate RGBA16F and RGBA32F outputs should
   demonstrate 16F range loss and 32F accurate finite preservation. Record the
   actual outcome (clamping/Inf), not an assumed overflow mechanism. Then pass
   that value through production deferred C0/C4 outputs and the real composite/
   final input path in both formats. Sample no texture attached for writing.
3. Only after those red controls, use `L = SOLAR / (PI*sin(alpha)^2)` and the
   selected wider targets. Require the production integrated flux to converge
   to SOLAR times the fixed cache within a stated discretization tolerance,
   with positive unit-cache and exact zero-cache controls. Vary Sun off-axis,
   FOV, viewport resolution and clear/cloud cache values. `fwidth(acos(dot))`
   edge smoothing and its minimum pixel angle may change integrated energy;
   test convergence before deciding whether a separate energy-preserving
   coverage rule is needed.
4. Validate both ping-pong allocations and mixed-format MRT combinations:
   C0/C4 32F with C8 16F, terrain C0 32F with C5 16F, and subsequent translucent
   writes/reads. Include GL framebuffer completeness/errors, alpha blending,
   resize/reload/clear and no stale snapshot or feedback. Shader names and
   format declarations alone do not prove the active Iris allocation.
5. Exercise linear and nearest sampling at resolved disc edges and opaque
   silhouettes. A single high-radiance texel linearly mixed with dark RGB can
   create a bright pre-tonemap transition; that is not automatically a bloom
   implementation or a behind-wall leak. Record HDR and displayed controls.
   Keep the existing unknown/hit/TIR and foreground-haze invariants.

`final.fsh` scales exposure and applies a shared `c/(1+max(c))` shoulder before
its five-tap *display-space* edge smoothing. Finite calibrated values remain
finite in float32 through the current exposure range, but Inf input can produce
NaN and must be rejected upstream. The display shoulder intentionally compresses
disc brightness; calibrate energy before it, not from a PNG. Do not change
exposure/tonemap simultaneously with the emitter red/green correction. The
deferred disc's derivatives still occur inside a varying sky-depth branch:
uniform all-sky flux controls isolate calibration, while a real sky/terrain
silhouette remains a separate derivative/antialiasing limitation.

The current underwater radiance convention and approximate finite-disc water
GGX lobe are not fully calibrated by matching the air emitter. Preserve their
existing regressions in this bounded slice and name remaining cross-interface/
finite-source transport approximations rather than claiming the entire Sun or
water realism goal complete.

## Later cloud-shape and source-closure work

The volume source should use incident angular illumination, while the forward
sky remains the ray's boundary radiance. This separation follows the
[equation of transfer](https://pbr-book.org/4ed/Light_Transport_II_Volume_Rendering/The_Equation_of_Transfer);
the present ambient closure is explicitly approximate. Use a controlled test:
with illumination held fixed, changing only background radiance should change
the result through cloud transmission, not also create local cloud light.

Add independent macro coverage/body envelopes and bounded erosion, preserving
an original procedural implementation. Test mean optical thickness/occupancy
against a fine reference when varying footprint; averaging threshold inputs is
not automatically equivalent to filtering the resulting density. Compare clear,
dusk and rain silhouettes and thick-base/bright-edge orientation in real views
without simultaneous exposure changes. Atmosphere/cloud multiple scattering,
ozone/sunset colour, calibrated Moon phases/night and temporal reconstruction
remain later, separately scoped improvements—not implemented features here.

## Inspected source snapshot

These hashes describe the concurrently edited working tree when inspected,
not a released/frozen 0.4 pack. Future root changes require reinspection; the
saved 0.3.3 captures above do not correspond to every file in this list.

```text
5a3d6a94a623118f6a675874a69d8251b4428d60c5b57cc44b3d2c9c297957b3  shaders/lib/clouds.glsl
9fb86309bdd082a6637ccab71fd34549b9da9a548b6148893c2e40681b1e3655  shaders/lib/atmosphere.glsl
a4919f0cf43f77a736b3b92b386c4b7625fc06f1df5d9e07f5160cfc29fb084e  shaders/prepare.fsh
b32770d63a7e1399b18ff8a526c4115d13116058f77fd4a1464af83452460c95  shaders/lib/illumination.glsl
16cf5a6c9b78b70b7cef735a58628742dffe8249fdba8443ede4a2a088ab2e34  shaders/lib/lighting.glsl
43f44c9272273542be0e6fcf5448007cf2c01fd7afca01ed82fa4fcab5cdbfaf  shaders/final.fsh
e43288346703a6a62cd66f11780491bca3552770c89a73b5132c2548c5ddb41f  shaders/composite.fsh
e6f799d997e7e5c08d07c54cb954fd1c6e5d86bc93471eb6ce09361fe3b2ada9  shaders/deferred.fsh
2e2073cfab36190d31f36af79e17a4e24208bb93f4189204c9442db440a0add9  shaders/lib/terrain.fsh.glsl
7e3dd317f377fbf021a66126c3fbbbc42eb977e8f4b38b73e8d5e0b81c5e1d34  shaders/gbuffers_water.fsh
f09fd04f422d6558b5df517f02ebd2db259c9cac93d3921dea515794b203aa34  shaders/lib/caustics.glsl
```

Disposition: no observed static Iris MRT topology blocker; receiver provenance,
component isolation, visual quality and runtime acceptance remain open. This
plan preserves the full goal rather than declaring an experimental slice done.

## Source-progress and pinned-depth addendum

Subsequent read-only review on 2026-10-02 inspected water SHA-256
`ae9c2989deb53b27129b65367c1cf4969e4d3b9a314b3838fca483c8327e3c04`.
The above-water caustic branch now explicitly requires `receiverKind == 1` and
uses C8's Sun component. Above-water tracing finishes its bounded refinements,
validates the final projection and carries receiver confidence; the caller
blends separately attenuated hit/proxy radiances. The formerly missing kind
gate is therefore **fixed in this inspected source**, not still pending. This
is source-progress evidence, not independent GPU/Minecraft acceptance of the
whole shoreline slice.

At this addendum's read, composite still hashes
`e43288346703a6a62cd66f11780491bca3552770c89a73b5132c2548c5ddb41f` and retains
the old underwater whole-colour multiply. Its Sun-only correction remains a
proposal. Both source hashes are working-tree observations, not frozen release
identities, and later changes should not be silently attributed to this review.

Additional `javap -c -p` inspection of the same pinned Iris JAR established:

- `RenderTargets` stores the main depth format as `currentDepthFormat` and
  creates `noTranslucents`/depthtex1 with that format and the same width/height.
  Resize/format changes resize the destination with the new source format and
  mark its depth copy dirty.
- Ordinary `copyPreTranslucentDepth` copies the full texture region with the
  selected `DepthCopyStrategy`. `fastest` chooses `Gl43CopyImage` when the GL
  entry point is available; its implementation uses `glCopyImageSubData`, level
  zero, both origins zero, matching width/height and one slice. No shader,
  reprojection, depth recomputation or resized sampling is involved.
- The [Khronos copy-image reference](https://raw.githubusercontent.com/KhronosGroup/OpenGL-Refpages/main/gl4/glCopyImageSubData.xml)
  describes a raw data copy without general format conversion. In that ordinary
  same-format path, an untouched opaque depth texel is bit-preserved. This is a
  source/API conclusion; the live selected strategy was not queried here.
- Dirty first/resize copies instead invoke `copyTexImage2D` with the same
  `currentDepthFormat` and source-sized rectangle. Older strategy fallbacks use
  same-size nearest depth/stencil blit or `copyTexSubImage2D`. Do not call every
  one of these paths a proven raw byte copy: the
  [copy-texture reference](https://raw.githubusercontent.com/KhronosGroup/OpenGL-Refpages/main/gl4/glCopyTexImage2D.xml)
  describes component conversion to the destination format. Positive first-frame
  and resize equality controls belong in the eventual runtime check.
- `DepthTexture` sets min/mag `GL_NEAREST`, unlike colour targets. Nevertheless
  `texelFetch(depthtex0, pixel, 0)` and `texelFetch(depthtex1, pixel, 0)` at the
  same integer pixel are preferable for the comparison: they avoid relying on
  either texture's sampler state or interpolated UV alignment.

Recommended minimal gate is therefore valid non-sky opaque depth plus exact
same-texel `depth0 == depth1`, with no reconstruction epsilon. It is stricter
than the previous distance-tolerance idea and appropriate to a copied depth
snapshot. If an exceptional copy path produces a mismatch, skipping a caustic
is a conservative false negative; widening the tolerance instead can focus the
wrong nearer layer. Keep the independent positive opaque-copy control so this
gate cannot pass merely by disabling all caustics.

Exact equality is not a material/provenance certificate. Depth-write-disabled
translucency, coplanar draws or separate surfaces quantized to the same stored
depth can still share the value; a C0-versus-C4 colour rejection check remains
only conservative supporting evidence. Test depth0 changed by just one stored
representable step (must reject), unchanged opaque pixels (must allow Sun-only
focus), and colour changed with depth held fixed (must reject under the proposed
colour check). Sky, resize/first frame and actual glass/particle routes remain
required controls. No such GPU/game checks were performed for this addendum.
