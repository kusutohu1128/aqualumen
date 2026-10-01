# Codex static review: v0.3.2 finite aerial scattering

Reviewed on 2026-10-02 JST (source snapshot at 2026-10-01 16:18:03 UTC).

This is a Codex source/design review, **not a fresh Claude Opus or Sonnet
review**. No Claude invocation, shader editing, GPU test, game operation,
installation or performance measurement was performed by this reviewer for this
audit. Runtime results and release validation belong in the root agent's reports.

## Disposition

No blocking source-level problem was found in the reviewed finite-air patch for
normal, finite Iris inputs. This supports proceeding to regression/runtime
validation, not evidence that the original screenshot symptom has been eliminated.

The Earth aerial path no longer blends the full forward sky-ray radiance into
opaque foreground pixels. It attenuates the existing surface radiance and adds
light scattered along the finite eye-to-first-depth segment. Water, Nether/End
fallback fog and surface shadow fallback remain outside this change.

## Physical model and normalization

Distances use the model's convention of one Minecraft block being one metre.
Let `h = max(position.y + cameraPosition.y - 63, 0)` and
`scale = HAZE_DENSITY * (1 + 3 * rainStrength)`.

```text
rhoR = exp(-h / 8000) * scale
rhoM = exp(-h / 1200) * scale
sigmaR = BETA_R * rhoR
sigmaM = BETA_M * rhoM
sigmaT = sigmaR + 1.1 * sigmaM

mu = dot(unitRay, sunDirection)
pR = 3 * (1 + mu^2) / (16 * pi)
pM = HenyeyGreenstein(mu, g = 0.76)
jDirect = SOLAR * cachedSolarTransmission(colortex6)
          * (sigmaR * pR + sigmaM * pM) * localSunVisibility
```

`sigmaT` has units of reciprocal metres. The `1.1` factor preserves the aerosol
absorption convention already used in the atmosphere model. The positive `mu`
sign represents forward scattering when looking toward the Sun. No horizontal
surface cosine is applied to the particle-scattering source. `SOLAR` remains a
chosen relative irradiance scale, not a calibrated SI radiometric measurement.
The scattering source has relative radiance-per-metre units.

For piecewise-constant coefficients and source over a segment of length `ds`,
the implementation uses:

```text
Tsegment = exp(-sigmaT * ds)
weight = (1 - Tsegment) / sigmaT
C += Teye * (jDirect + jAmbient) * weight
Teye *= Tsegment
outputRGB = surfaceRGB * Teye + C
```

Operations are componentwise RGB. For optical thickness `x < 0.001`, the weight
uses `ds * (1 - x/2 + x*x/6)`, avoiding float cancellation for short paths.
Distance zero and HAZE zero return transmission one and radiance zero. Accumulated
transmission is applied before updating it; opacity is not applied twice. This
finite-boundary formulation follows the [equation of transfer](https://pbr-book.org/4ed/Light_Transport_II_Volume_Rendering/The_Equation_of_Transfer).

### Diffuse ambient closure

The existing five-direction helper estimates horizontal sky irradiance `E`;
for constant sky radiance `L`, its weights give `E = pi * L`. The new source is:

```text
ambientRadiance = E(colortex7) / (2 * pi) * skyExposure^2
jAmbient = (sigmaR + sigmaM) * ambientRadiance
```

This explicitly approximates the upper hemisphere as isotropic diffuse
illumination: `2*pi` steradians times the isotropic phase average `1/(4*pi)`
gives `L/2 = E/(2*pi)`. It is not an exact anisotropic HG hemisphere integral.
The diffuse samples are taken once per pixel, not once per integration step.
Eye sky brightness gates this approximate illumination, not extinction or local
direct lighting. Shaded air may therefore still receive diffuse illumination;
genuinely sunlit air in front of an opaque wall may receive direct illumination.
Volume in-scattering has no surface-normal cosine term; see [volume scattering processes](https://pbr-book.org/4ed/Volume_Scattering/Volume_Scattering_Processes).

## Geometry, visibility and routing

- `eye = relativeWorld(vec3(0))`; midpoint samples are `eye + unitRay * t`.
  The interval length is the reconstructed first-depth distance, capped by `far`.
  This handles inverse-modelview translation instead of incorrectly scaling
  that translation with the ray's interpolation parameter.
- This is **not a fixed 1.62-metre eye-height correction**. Iris's misleading
  “feet-player” terminology does not mean the player's feet: its distinction
  from eye-player space includes head/camera translation and view bobbing.
  [Iris coordinate-space documentation](https://shaders.properties/current/how-to/coordinate_spaces/)
  explains the convention. The screenshot does not establish the actual matrix
  translation magnitude.
- A non-positive/near-zero projection `w`, out-of-bounds shadow coordinate or
  NaN coordinate produces zero **volume direct** visibility. Unknown shadow
  coverage is not assumed illuminated. Direct visibility also fades to zero
  over 80–100% of the configured shadow distance.
- Existing terrain `shadowVisibility` fallback is unchanged. The new function
  is not a blanket change to distant terrain lighting.
- Earth uses the new finite model, with cloud-free `colortex7` diffuse samples
  and cloud-attenuated `colortex6` solar cache. Nether/End retain their previous
  dimension-colour fog; the underwater branch is unchanged. Composite alpha
  remains one.

## Regression requirements and evidence boundary

The decisive source-level invariant is: hold surface RGB, depth, local shadow
visibility, solar cache and diffuse quadrature results constant; change only a
blocked forward sky-radiance cone outside the diffuse sampling footprints.
Foreground RGB must remain unchanged. The reviewed implementation has no direct
forward-sky lookup in its Earth aerial source, so its dependency structure
satisfies this invariant.

Runtime validation should additionally cover blocked versus illuminated direct
light, unknown shadow coverage, zero distance/density, a constant-coefficient
analytic reference and translated-eye geometry. Coordinate-rebasing tests must
transform the related camera/shadow data consistently, not merely change one
matrix while changing the physical scene.

The user's `flameshot-20261002-004054-491743850.png` shows a bright Sun above the
terrain crest and a veiled grass/dirt wall. It does not by itself distinguish
behind-wall light leakage from legitimate scattering in illuminated air in
front of the wall. Native controlled probes and guarded old/new fixtures are
not exact replays of that screenshot. Do not describe their success as proof
that every apparent shaft over solid land is physically invalid or eliminated.
Re-checking the original scene is a separate release-validation task.

## Accepted limitations and robustness notes

- Ten default midpoint shadow samples can miss narrow shadow intervals; finite
  ray integration does not provide exact geometric volumetric visibility.
- Direct solar transmission is cached at the camera, not recomputed at every
  air sample. Diffuse illumination uses a clear-sky five-direction closure,
  not local cloud/ground transport or full multiple scattering.
- Rain/HAZE scaling, eye-exposure squaring and sea-level offset 63 are modelling
  approximations. Extinction changes physically with path length, but the
  complete weather/sky system is not radiometrically calibrated.
- The inherited `depth < 0.999999` surface/sky classification can misclassify
  valid depths extremely near the far plane. This patch does not resolve it.
- Normal finite Iris uniforms are assumed. NaN projected coordinates are
  rejected, but `clip.w = +Inf` with finite XYZ can map to apparently valid
  coordinates; non-finite input ray/distance is not separately guarded.
  Additional invalid-input guards would improve defensive robustness, but no
  such corrupted-matrix failure was observed by this source audit.

## Reviewed source SHA-256

Hashes were read from the actual files, not inferred from a release ZIP name.
These identify the reviewed snapshot; later changes require a renewed check.

```text
0aa1cf61b793606c832d395bc4c3a9d4ce37c52754b00534d3a410a8ab74eb1c  shaders/lib/aerial.glsl
e43288346703a6a62cd66f11780491bca3552770c89a73b5132c2548c5ddb41f  shaders/composite.fsh
664b94fc614929b022fb306f9b11648630a1cc796d9f4d73e7f13b0c394573c2  shaders/lib/atmosphere.glsl
b32770d63a7e1399b18ff8a526c4115d13116058f77fd4a1464af83452460c95  shaders/lib/illumination.glsl
b107903b98adc5bfd31367f49323371738f0148585d4132c4fb7e0f109778045  shaders/lib/shadows.glsl
a7be475e81c360d7c82609f9f643aaa7b08ce5b48fb44d53c24504cc9f0d775f  shaders/lib/uniforms.glsl
f4f369a783a8c8d0bfe91d71405d91ab30b063c0d2fa40297866d900f00080a9  shaders/prepare.fsh
```
