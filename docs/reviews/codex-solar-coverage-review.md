# Solar disk coverage review — 2026-10-02

Read-only CPU/source review by the water-quality agent. No GPU job, game action,
shader edit, or test relaxation was performed for this review. Scope is the
direct-Sun disk/terrain energy relationship, not complete sky, water, weather,
or Iris visual acceptance.

## Finding

The clear-air correction is mathematically justified and the supplied native
production-main RED/GREEN evidence is nonvacuous. No blocking defect was found
in the circle/parallelogram area construction for its local linear-footprint
model. This is **exact circle/polygon area within an approximate pixel mapping**,
not exact spherical-pixel integration for arbitrary cameras or refracted rays.

The initial clear GREEN did not establish rainy-weather coherence: at that
stage the disk omitted the terrain's existing `1 - .85 * rainStrength` factor.
During this review root independently recorded weather RED, applied that factor
once in `sunDisk`, and recorded weather GREEN. The two increments remain
separate evidence; the factor is an existing empirical weather convention,
not a calibrated precipitation transport model.

## Mathematics and implementation

- `atmosphere.glsl:154–163`: for constant radiance `L` within angular radius
  `a`, perpendicular beam irradiance is
  `2*pi*L*integral_0^a(cos(theta)*sin(theta)) = L*pi*sin(a)^2`.
  Dividing the admitted beam by `pi*sin(.00465)^2` therefore has the correct
  units and normalization. The projected solid angle is `6.792859755e-5`.
  The previous `20 * SOLAR` disk predicts a ratio near `.00135857`, consistent
  with the observed old ratio near `.001357`, rather than unity. This is an
  RGB rendering-unit convention, not measured solar spectrum/irradiance.
- `:110–130`: each directed polygon edge is split at the two unit-circle
  crossings. The interior part contributes its signed triangle area; exterior
  parts contribute signed `atan(cross,dot)/2` sectors. Summing four edges gives
  intersection area independent of polygon winding after the final absolute
  value. The explicit `discriminant <= 0` exterior-sector path correctly treats
  exact tangency: a midpoint touching the circle does not make the exterior
  segment an interior chord. Zero-length edges contribute zero.
- `:132–152`: a normalized Sun direction and the alternate pole axis give a
  nonsingular orthogonal basis. Gnomonic coordinates avoid small-angle `acos`
  cancellation; near the disk, the cosine denominator is positive and nowhere
  near its `.0001` safeguard. `dFdx`/`dFdy` provide two vector footprint axes,
  unlike scalar `fwidth(angle)`. The radius bound is the furthest parallelogram
  corner, so full-inside/full-outside early cases are conservative within that
  footprint. Fractional coverage, not a blur halo, retains an unresolved disk's
  area in the model. Coverage is clamped to `[0,1]`; nearly degenerate footprints
  use a point limit. Float intersection/cancellation errors and derivative
  accuracy still exist; the clamp alone is not proof of energy conservation.
- `deferred.fsh:13–19`: the complete sky expression is now evaluated before the
  varying depth selection. Within the disk helper, derivatives likewise precede
  varying coverage branches. This removes the previous opaque/sky control-flow
  derivative problem. `earthAtmosphere()` is dimension-uniform. GLSL permits
  implementation-dependent derivative accuracy and does not define derivatives
  inside nonuniform conditionals; see the primary
  [GLSL 3.30 specification](https://registry.khronos.org/OpenGL/specs/gl/GLSLangSpec.3.30.pdf).
- The coverage helper uses GLSL 3.30 fragment operations, not compute, subgroup,
  doubles, or newer derivatives. Real NVIDIA compilation under `#version 330`
  is useful evidence, but the host is a GL 4.6 compatibility context, not a
  separate strict-3.3 device test. The overall pack's ripple compute path has
  its own higher-version requirements.

## Dynamic range and producer/consumer proof

At cache transmission one, the sharp red disk radiance is about `264984`, above
RGBA16F's largest finite value `65504`. Retaining C0 and immutable C4 in RGBA32F
is consequently necessary for this representation; merely fixing the scalar
while keeping both half-float targets would clip/overflow the source. C5/C8
hold receiver direct radiance, not the disk, and remain half-float. The cache
and ordinary sky LUT also remain half-float; disks are not baked into that LUT.
The two 32F targets increase memory/bandwidth; no live frame-time claim follows.

The fixture compiles the unchanged actual terrain and deferred programs,
queries formats, renders a white Sun-facing Lambertian receiver, retains its
C5-to-C8 direct-source snapshot, and independently integrates the deferred
sky with spherical corner-ray areas and cosine weights. Zero-cache, positive
beam, finite-output, C0/C4 equality, and zero sky C8 checks precede the energy
assertion. Sampled allocations and output FBO allocations are distinct.
This is stronger than a helper-only formula test. It does **not** run actual
Iris allocation/metadata parsing or the real `prepare` cache producer: prepare
is read for its public declarations and the fixture injects a controlled cache.

Supplied NVIDIA RTX 3080 Ti / driver 580.173.02 logs use a 512² sky viewport,
2-degree vertical FOV, centered zenith Sun, cache one, black ordinary sky, and
independent quadrature refinement error `2.90222e-10`:

| Increment | RED sky/terrain beam | GREEN sky/terrain beam |
| --- | --- | --- |
| Clear, rain 0 | `.001357585 / .001357032 / .001357143` | `1.000526536 / 1.000123490 / 1.000205517` |
| Weather, rain 1 | `6.667145008 / 6.666715092 / 6.668036781` | `1.000071614 / 1.000007122 / 1.000205372` |

Clear integrated RGB is `(17.99999934,17.60000075,17.00000020)`; remaining
terrain discrepancy is within half-float C5/C8 quantization. The weather GREEN
integral is `(2.69999953,2.63999974,2.54999966)`, matching the separately admitted
`.15 * SOLAR` beam. These are bounded acceptance results, not new GPU runs by
this reviewer.

## Remaining limits

1. Normal gameplay FOV, off-axis/rotated/skewed projections, truly subpixel disks
   at multiple phases, opaque silhouettes, horizon crossings, and actual Iris
   HDR readback remain separate acceptance. The centered narrow-FOV fixture
   makes the gnomonic mapping particularly close to affine. In general the
   local derivative parallelogram differs from a projective quadrilateral and
   from solid-angle-weighted spherical coverage. A smaller max error in this
   fixture must not be promoted to all-view exact energy preservation.
2. `gbuffers_water.fsh:245–257,275,295` has Snell/TIR and Fresnel, and evaluates
   directional sky before the divergent hit/TIR branch. It still transports
   transmitted radiance without a general refractive `L/n^2`/etendue convention.
   Radiance transport across unequal IORs requires squared-index scaling,
   distinguished from importance transport; see
   [PBRT's dielectric BSDF derivation](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF).
   Underwater compressed disk coverage near the critical angle has a nonlinear
   pixel mapping. This correction therefore does not establish physically
   complete underwater solar energy. Do not insert an arbitrary `eta^2` into
   the separately tested collimated bottom-beam flux to compensate.
3. Atmosphere/cloud multiple scattering, spatial observer-to-cloud coupling,
   empirical rain suppression, moon phases/normalization, and rough-water
   specular quadrature remain approximations. The Moon still uses its older
   scalar `fwidth` treatment and is not covered by this Sun energy test.

## Evidence fingerprints

Source inspected after the separately recorded weather update:

```text
atmosphere.glsl 89e1d66b88144e018e3d7b012a3e92319209070f38b6e1918c505f965b29ece4
prepare.fsh fa5d6cd1f10e9313dba9a4927d12f19ed9d6443dfbcb7ac1219dd1ae4813c790
deferred.fsh ad9e840596300f4a5ffacc8f212d0e3f00290e06fbe27a347d7bd60a2b1844ef
lighting.glsl 16cf5a6c9b78b70b7cef735a58628742dffe8249fdba8443ede4a2a088ab2e34
```

Logs, preserved independently from this document:

```text
build/solar-radiometry-v0.5-red.log b722b48307204ad7d1cf5bd489db543a92f9eab39c4b3c762fa9aa898fa7a6d7
build/solar-radiometry-first-green.log 6e693e3030e338f4f89a8e36541dd084271ac978afea0e7bf9b6f0852419b491
build/solar-radiometry-weather-red.log 952f2cb5a1e301267f1de948c3b825e4ef5cb00e1660112cea28dbe7dff7dbe0
build/solar-radiometry-weather-green.log 9e28ffb869423aee7aab2224877099e7ffb8d83852611cb240d628475ea73a1c
```

## CPU-only next-coverage/range recommendation

The subsequent header inspected for this recommendation has SHA
`f9ce5c2ad14caf548f0385d030b2fbba8b8b0933cbe5c6ef88adb1a864aa226a`.
It now accepts rectangular viewport dimensions and vertical FOV, allocates and
reads corresponding full-size outputs, and uses both rounded float inverse
projection focal lengths in its independent corner-ray integration. The Sun
remains centered; the terrain receiver/cache/zero controls remain fixed. No
new GPU result is claimed in this section and no harness edit was made.

Recommended order, keeping one behavioral increment at a time:

1. Establish the existing header's `2560x1440`, vertical-FOV `70°`, rain-zero
   centered baseline if not already measured by root. The source disk radius
   is about `4.78147` pixels, unlike the large resolved narrow-FOV fixture.
   The independent expectation remains `(18,17.6,17)` integrated perpendicular
   irradiance and unity versus the actual white receiver beam, not a new
   guessed apparent-brightness threshold.
2. Smallest high-value next coverage slice: repeat that viewport with only a
   horizontal principal-point shift of `delta = .37` pixel. Keep world Sun,
   ordinary sky/cache, receiver, weather, and FOV unchanged. This breaks the
   centered even-sized viewport's symmetric pixel phase without a new scene or
   rotated light. Expect the same integrated beam in each RGB channel, within
   the existing independent quadrature/declared-format bounds and physical
   unity gate. Recalculate corner-ray/cosine weights from the exact matrices,
   retain zero-cache and C0/C4/receiver-attribution checks, and record phase as
   fixture input. This tests raster phase, **not** a genuinely angular off-axis
   nonlinear mapping, nor a disk smaller than one pixel.
3. Smallest range control: reuse the resolved `512² / 2°` frame, independently
   qualify at least one camera-pixel cone entirely inside the angular disk,
   and verify `C0 == C4` retains the uniform disk radiance. At cache one/rain
   zero, red expectation is `18/(pi*sin(.00465)^2) = 264984.125`, well above
   `65504`. An explicitly labeled, allocation-only RGBA16F diagnostic negative
   control should lose that range or become nonfinite; it must **not** silently
   relax the production-declaration/format/finite checks. This distinguishes a
   real source-range loss from a shader coefficient or cache mistake without
   changing shipping GLSL. A negative control is evidence about range, not a
   second shipping format.

For the proposed phase, column-major perspective matrix element
`P[8] = o = -2*delta/width` moves the fixed forward Sun to pixel coordinate
`width/2 + delta`; the corresponding inverse element is
`inverseP[12] = o/focalX`. The other source/view quantities stay fixed. If a
later test instead rotates the view, the sky `sunPosition` must be transformed
from the same fixed world Sun: the current hardcoded `(0,0,-1)` sky uniform
would otherwise rotate the light along with the camera and defeat an off-axis
test.

The current aperture guard `4*atan2(tx*ty,sqrt(1+tx²+ty²))` assumes a symmetric
rectangle. After principal-point shift, changing only ray reconstruction while
keeping that oracle would introduce a fixture error. Use the independent
asymmetric bounds from the same rounded float matrices:

```text
xLo=(-1+o)/focalX; xHi=(1+o)/focalX
yLo=-1/focalY;     yHi=1/focalY
F(x,y)=atan2(x*y,sqrt(1+x*x+y*y))
Omega=F(xHi,yHi)-F(xLo,yHi)-F(xHi,yLo)+F(xLo,yLo)
```

This is a corrected geometric reference, not a weaker convergence tolerance.
In ideal double arithmetic for `.37` pixel at `2560x1440 / 70°`, symmetric
versus shifted apertures already differ by about `3.05e-8` relative, above the
existing `1e-9` aperture guard. All corner rays and the analytic aperture must
use the same actual rounded matrix values. A mere successful unshifted wide-FOV
run cannot establish phase stability, half-float failure detection, exact
underwater refractive etendue, or live Iris/FPS acceptance.
