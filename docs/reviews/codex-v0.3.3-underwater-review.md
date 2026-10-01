# Codex static review: v0.3.3 underwater directional sky

Reviewed on 2026-10-02 JST (source snapshot at 2026-10-01 17:44:17 UTC).

This is a **Codex static source/design review**, not a fresh Claude Opus or Sonnet
review. No Claude invocation, shader modification, GPU test, game operation,
installation or performance measurement was performed by this reviewer for this
audit. The source hashes below identify the frozen review snapshot; final native
and Minecraft validation was still pending at this snapshot and is not asserted
here. Runtime results belong in the release verification reports.

## Disposition

No blocking source-level problem was found in the reviewed patch for normal,
finite Iris inputs. The patch separates actual screen-space opaque hits from
sky observations and unknown trace failures, so an original-screen-UV fallback
is no longer mistaken for a successful underwater refracted receiver.

The user's `flameshot-20261002-021552-564507001.png` visibly contains a rectangular
switch between two cloud mappings inside the underwater window. This review
inspected that image and the source; it did not replay the user's exact scene.
Controlled native fixtures are not exact screenshot replays, and source review
alone does not establish that every underwater artefact is resolved.

## Three receiver states

`refractionTrace` initializes its new output to zero before any early return.

| Kind | Meaning and assignment | Underwater background |
| --- | --- | --- |
| `0` | Unknown: out of screen, near-tangential view ray, invalid projection, rejected foreground or non-convergence | `mix(caveAmbient, directionalSky, skyAccess^2)` |
| `1` | Positive-distance, converged opaque-depth receiver accepted by the existing trace checks | `texture(colortex4, hitUV).rgb` |
| `2` | A sampled screen depth was classified as sky | Full `directionalSky`, without the approximate sky-exposure gate |

Returning the original UV does not set kind 1. A returned sky UV is not used to
sample the finite camera image underwater. Above water, the old `colortex4`
fallback policy is retained, including its existing foreground/upper-surface
checks and caustic routing.

Kind 2 means **screen-space sky observation**, not proof of an unobstructed
world-space ray. Screen-space depth cannot reveal hidden or offscreen objects.
The inherited `0.999999` surface/sky threshold also remains an approximation
near the far plane.

## Full directional sky and cave compatibility

The sky background is evaluated using the transmitted world direction:

```text
directionalSky = sampleSky(colortex6, transmittedWorld)
               + sunDisk(transmittedWorld, sunDirection, colortex6)
               + moonDisk(transmittedWorld, sunDirection)
```

The LUT contains atmosphere and clouds, but not the analytic Sun/Moon discs.
`environmentSkyRadiance` shares their complete expression with `deferred`;
deferred's expression is therefore unchanged in meaning. Underwater sky colour
is no longer obtained by projecting an artificial 48-metre sky point into the
camera's rectangular viewport. The trace's travel limit still constrains real
geometry detection, not the directional sky lookup itself.

An unknown trace does not automatically produce bright sky in a closed cave.
It uses the existing neutral `caveAmbient` closure and local sky-exposure blend.
A positively observed opening is not incorrectly darkened just because local
lightmap sky exposure is low. Moving incident irradiance/scatter/cave ambient
earlier in `main` does not change their coefficients or calculations.

No new world-Y sign cutoff was added for the sky fallback. Side-facing flowing
water must not be treated as a horizontal water plane, and a blanket upward-ray
gate would create another artificial terminator near tilted wave facets.

## Total internal reflection and derivatives

The existing water-to-air indices `1.333 -> 1.0`, exact unpolarized Fresnel
function and final Fresnel blend remain unchanged. The existing water-only
scatter/SSR reflection environment is retained underwater; this is not a full
dielectric transport rewrite. Refraction has no transmitting solution during
total internal reflection; see [dielectric reflection/transmission](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF).

The directional sky helper is evaluated under the uniform underwater state
before the divergent trace/hit/Fresnel branches. A zero refracted vector is
replaced by a safe upward direction for that evaluation only, preventing zero
normalization. Its evaluated sky is unused in the final pure-reflection result.

This placement avoids introducing disk derivatives inside the new varying hit
branches. It does not redesign deferred's pre-existing sky-depth branch, nor
guarantee ideal antialiasing at a sharp total-internal-reflection boundary:
neighbouring safe-substitute directions can still affect derivative widths.

## General eye-coordinate correction

The final water view vector is:

```text
eye = relativeWorld(vec3(0))
v = normalize(eye - worldPosition)
```

If the inverse model-view maps a view position to `P = R * viewP + T`, then
`eye = T` and `eye - P = -R * viewP`. The translation cancels rather than
silently assuming the eye is the origin of that coordinate basis. For zero
translation this reduces to the former vector; nonzero translation intentionally
corrects both reflection and refraction directions on either side of the water.
Above-water trace policy and optical coefficients are otherwise unchanged.

This is **not a fixed 1.62-metre height correction**. Iris's “feet-player” name is
misleading: the distinction from eye-player space accounts for head/camera
translation and view bobbing, not a universal feet-to-eye offset. See [Iris coordinate spaces](https://shaders.properties/current/how-to/coordinate_spaces/).
Neither screenshot inspection nor this review establishes the actual live
translation magnitude. A coordinate-invariance test must transform geometry,
view/inverse-view, camera and shadow data consistently while preserving the
physical scene.

## Required verification and remaining limits

- Hold transmitted direction and sky data fixed, vary only the old camera-image
  sky mapping: underwater sky/unknown output must not acquire that image mapping.
  Changes to real converged opaque receiver colour must still affect output.
- Check observed sky, closed-cave unknown, exposed unknown, actual opaque hit,
  viewport exits, travel-limit failures and near-tangential trace rays separately.
- Check the total-internal-reflection transition, finite output and the Sun/Moon
  contribution through the transmitting window. The safe evaluation direction
  must not contribute to a pure-reflection pixel.
- Independently check translated-eye invariance and the above-water control;
  do not conflate coordinate correction with the primary sky-routing regression.
- Revisit an underwater open-water view, a cave mouth, a closed aquifer, side
  flowing water and the original reported scene in Minecraft.

Screen-space tracing can still miss offscreen or hidden coast/cave silhouettes
and then substitute an environment approximation. The exposure closure is not
an occlusion solver. Real-geometry traces still use the inherited iteration,
travel and depth-tolerance limits; wave self-occlusion and full multiple-interface
transport are not solved by this patch. Cloud/solar caches remain camera-based
approximations. Water extinction/scattering coefficients and the v0.3.2 finite
aerial model are unchanged in this snapshot.

## Reviewed source SHA-256

Hashes were read from the actual files. They are not a release ZIP hash or a
runtime-pass certificate. Any subsequent shader change requires a renewed check.

```text
4c6e8363ce606892a2860e96e2d7ee5f5d9cc75f1710a985a5c59abaa50a0327  shaders/gbuffers_water.fsh
9fb86309bdd082a6637ccab71fd34549b9da9a548b6148893c2e40681b1e3655  shaders/lib/atmosphere.glsl
e8fbab57f5f135853ed41298c82a8a2026de70904c511927faf02fb0f5944d55  shaders/deferred.fsh
60ff29021470ca5869652286493bb0583dcd2800a1ff9590bd912ac8e0e07c48  shaders/lib/water.glsl
0aa1cf61b793606c832d395bc4c3a9d4ce37c52754b00534d3a410a8ab74eb1c  shaders/lib/aerial.glsl
```
