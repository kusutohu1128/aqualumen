# Water incident-Sun leg: diagnosis and one proposed RED

Read-only source/image review, 2026-10-02. Only this plan was written. No GPU
context, Minecraft/UI/lifecycle action, shader/test edit or benchmark was run.
The proposed numerical results below are predictions, not measurements.

## Evidence and limits

Viewed the actual 0.4.0 [coast](../../reports/2026-10-02-v0.4.0/after/coast-day.png)
and [river](../../reports/2026-10-02-v0.4.0/after/river-day.png) stills and their
0.3.3 comparison captures. Both current views retain large bright cyan/pale-green
bottom windows and strongly angular dark/clear boundaries. Some boundaries
follow real stepped Minecraft geometry; others vary with the surface's reflected
and transmitted fields. A still cannot establish which branch made a given
edge, temporal stability, or the water depth of every visible receiver. Clouds
and waves were not phase-frozen between captures; no pixel-causal A/B claim is
made here. The matching scene/pack metadata is already covered by the exported
[independent audit](../../reports/2026-10-02-v0.4.0/INDEPENDENT-AUDIT.md).

Current source confirms a narrower transport omission:

- `lib/lighting.glsl:7–13` shades the receiver with air-directed Sun and exports
  `sunRadiance`; `lib/terrain.fsh.glsl:15–18` writes C5. Deferred copies this
  **raw, dry-lit** direct contribution into C8 (`deferred.fsh:19–22`).
- Above-water main changes the proved receiver's C8 by the caustic focus delta
  (`gbuffers_water.fsh:241–248`), then attenuates its receiver-to-interface/view
  leg (`251–259`). There is no surface-to-receiver beam transmission.
- Underwater composite similarly adds a focus delta to raw receiver Sun
  (`composite.fsh:36–42`), then attenuates only receiver-to-eye distance
  (`44–47`). With a flat surface, focus is one, so its active surface height
  does not reduce the direct receiver contribution at all.
- `shadowTranslucent=false` and an opaque Sun shadow map do not supply the
  missing spectral water beam transport. The caustic depth envelope is a
  focusing regularization, not base-Sun extinction.

This establishes an omission in the current approximation, **not** that this
omission caused every cyan or jagged feature in the images.

## Ranked alternatives and distinguishing predictions

1. **Missing incident Sun path: over-energetic directly lit submerged bottom.**
   If this is responsible for excessive bottom brightness, increasing only
   surface-to-bottom water distance, while holding the eye leg and raw receiver
   illumination fixed, must reduce the isolated direct response. Current source
   predicts no reduction for a flat interface. Correcting it affects direct Sun,
   not arbitrary diffuse/block RGB. It does not by itself predict smoother
   geometric shore silhouettes.
2. **Remaining discrete depth/SSR/proxy transitions.** The 0.4 confidence patch
   fixes the demonstrated continuous-bed handoff, not all occlusion silhouettes
   or reflected-source switches. If these dominate the jagged dark patches,
   they will persist with zero direct-Sun receiver energy and follow camera/depth
   visibility boundaries. Incoming Sun correction cannot repair those paths.
3. **Geometry versus shore-normal mismatch.** Vertex displacement uses depth64
   (`gbuffers_water.vsh:26`, `waves.glsl:65`); the fragment uses a screen-derived
   bottom and attenuates waves over 0.035–0.8m (`waves.glsl:56–59`). At real banks
   the geometric water face and its optical normal can therefore disagree.
   A separate legal `WAVE_HEIGHT=0.0` A/B would suppress wave-driven facet/border
   changes, but not remove genuine one-block bathymetry steps. This is a later
   geometry experiment, not part of the first incident-leg test.
4. **Chosen RGB transport and strong source contrast.** Extinction
   `(0.32,0.085,0.035)/WATER_CLARITY` and scattering albedo
   `(0.0045,0.018,0.045)` are chosen effective RGB appearance parameters, not
   measured ocean calibration (`water.glsl:22–32`). Bright sand through these
   unequal transmissions can become cyan even with correct provenance. With
   these unchanged coefficients, adding another water leg removes red faster
   than blue: it darkens direct Sun but can **increase the blue/red ratio**.
   Neither desaturation nor photorealism follows automatically. A later
   coefficient/material calibration must be judged independently, not used to
   conceal an incorrect receiver or light path.

## One tracer bullet: incident-depth response in production composite

Use the actual `composite.vsh/fsh` program and its sampled texture/uniform
interfaces, with a separate RGBA32F output attachment. No copied transport
shader or private-function replacement. This deliberately starts underwater:
the camera and receiver remain in the same medium, avoiding an additional
view-side air/water boundary and its radiance/etendue convention.

Fixture:

- Horizontal homogeneous water, existing public `WAVE_HEIGHT=0.0`, inactive
  contact sources. Set `aqualumenActive=1` so the known local surface plane is
  available; this flag does not imply nonzero ripple forcing.
- Downward camera, fixed opaque horizontal Lambertian bed at camera-relative
  Y=-1m, fixed eye and identical matching depth0/depth1/C8 pixel grids. Bed
  and shadow are unoccluded; use a positive fixed zenith Sun, fixed weather,
  nonnegative background receiver radiance B, and positive raw direct receiver
  radiance D. D is the pre-water C8 Sun attribution, not already attenuated.
- Surface heights +0.5m and +2.5m relative to the fixed eye: incoming distances
  d1=1.5m and d2=3.5m, outgoing eye distance remains 1m at the centre pixel.
  Both surfaces stay above the eye; all geometry remains inside the known
  connected water volume. No foreground interface is falsely paired with C8.
- For each height, draw `C0=B+D,C8=D` and `C0=B,C8=0`. Keep every other input,
  including solar cache, shadow and medium illumination, identical. The latter
  is the receiver's zero-direct-attribution control, not switching off the Sun
  illuminating the entire water volume. Their difference isolates the receiver
  direct response R(d); common medium in-scattering cancels.

For a homogeneous medium beam transmission is exponential and multiplicative.
The receiver's direct contribution needs both the incoming and outgoing legs,
not just the eye leg. This is the standard
[PBRT transmittance model](https://pbr-book.org/4ed/Volume_Scattering/Transmittance).
At normal Sun incidence, the incoming direction is straight down. A consistent
surface Fresnel entry factor is the same at both heights and cancels in the
ratio, as does the fixed outgoing transmission. Thus the single behavior is:

`R_c(d2) / R_c(d1) = exp(-sigma_t,c * (d2-d1))`.

With the project's unchanged clarity1 and extinction contract, a 2m incident
increment predicts approximately `(0.527292,0.843665,0.932394)` in RGB. Current
source instead predicts `(1,1,1)` because focus=1 and no incident transmission
exists. Compute the CPU exponential from that documented optical contract, not
by invoking/copying a GLSL helper. Assert a positive finite R(d1), valid alpha,
determinism and the ratio within native numerical tolerance. The positive
response prevents making the test pass by deleting all receiver Sun.

Normal-incidence horizontal flux avoids incorrectly replacing irradiance with
a bare refracted-radiance n-squared factor. PBRT explicitly distinguishes this
[radiance transformation](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF).
The ratio intentionally does **not** certify the absolute Fresnel entry factor;
that is a later behavior after this first RED/GREEN, not a bulk imagined test.
Because the paired subtraction cancels medium in-scattering, it also does not
certify depth-dependent Sun illumination of the scattering water itself. The
current homogeneous source approximation uses incident sky/Sun illumination
without solving its water-entry path at every scattering point; that remains
a separate transport limitation after a receiver-only incident-leg correction.

## Boundaries for the later implementation

Wait for GPU ownership and record RED before changing production source.
Attenuating only the caustic delta cannot pass: flat-water focus is already one,
and the raw base Sun inside total receiver RGB still needs correction. Preserve
the raw-Sun snapshot contract and replace only its contribution; do not multiply
all diffuse/Moon/block receiver light by this one collimated Sun path or apply
incoming transmission twice. Retain existing positive attribution, unknown-hit,
matching-depth/layer rejection, shore continuity and underwater sky/TIR/eye tests.

This first fixture assumes a known horizontal connected water volume and flat
receiver. Oblique Sun needs Snell's incoming water direction and d/cos(theta_t);
arbitrary receiver normals, bent-ray shadows, uneven surfaces, separate pools,
multiple scattering and unknown above-water proxy depths are separate unresolved
approximations. A global nearest surface is not proof of water membership.

After one successful causal slice, use root-controlled matched actual coast,
river and underwater stills/motion to assess brightness, hue and remaining
boundaries. Neither this plan nor a future native pass establishes the complete
water/light realism goal or current/live Minecraft FPS.
