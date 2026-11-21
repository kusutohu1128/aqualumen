# Native Sun source integration: predeclared bounded experiment

2026-10-03, before any native run of this packet. The previous controlled-Gaussian
checkpoint made progress, but did not implement the native Sun. The broad user
goal is still active; no release, installation or acceptance is authorized by
this experiment alone.

## Question and independent boundaries

Can the original water main replace only its sharp solar contribution with a
positive light-direction integral using the same raw observed n/v, covariance,
inverse-Snell branch and legacy Fresnel/transport units? The source radius,
SOLAR, transmission-cache addressing and single weather factor remain native.

Native `sunDisk` uses derivative-based pixel coverage. A central physical sharp
cap integral is NOT an exact oracle for that filtered source. Consequently this
packet distinguishes a central sharp-Sun response gate from native pixel-filter
equivalence. A sharp-reference failure alone must not be called a proved bug in
the continuous filtered legacy integral. Pixel-footprint, receiver visibility,
critical limits, actual Iris motion and visual/FPS acceptance remain open.

Ranked predictions fixed before testing:

1. Fixed GH3 slope nodes miss the small Sun: qualified legacy response can be
   much smaller than a converged sharp-cap response; new light-domain nodes
   should match the independent sharp-cap reference at the same actual inputs.
2. Pixel coverage changes the interpretation: 2-degree and 1-degree apertures
   are separate, fixed qualification fixtures, not adaptive settings to force
   a pass. Their measured differences cannot prove a general filtered limit.
3. Cache/weather units may be mixed: measured positive/zero-cache responses
   and a fixed half-rain control should expose duplicated weather or gain.

## Immutable parents and source control

- Guard-v2 ZIP: `9c104ebebe77d5fd12cea95f75e30e686668a8b4605a4a5ea6227cc6e0ca5e85`.
- Guard expanded FS: `62837f5fe0cdfa21c509be48db408941164d7b5a96c853d57c5c4de0a09698b3`.
- Resolved parent ZIP: `3a83e837628f4b0b21617d1468baa3d2e6fd659b5a758800cfa301d75646ab26`.
- Atmosphere: `89e1d66b88144e018e3d7b012a3e92319209070f38b6e1918c505f965b29ece4`.
- Existing kind1 helper/builder, wave/old residual math and old packets remain
  unchanged. New Sun tags must strip to the exact guard FS, and outer residual
  tags to the exact resolved FS. No native environment-return substitution.
- The first Sun helper is pass-through STUB with applied=0. Preserve its ZIP and
  native failure before adding the cap implementation. Same probe binary and
  inputs must execute the cap candidate. CPU construction passes are not GPU RED.

## Fixture and response reduction

Use the original VS/TCS/TES/FS, phase120, 257x257 RGBA32F eight-MRT/depth exporter,
known uniform column and open opaque depth. Projection aperture is fixed at
2 degrees for the primary and 1 degree for a separate qualification. The
effective-footprint floor stays .035; no Sun widening or derivative disabling.
Other geometry, view basis, cache storage and source units stay unchanged.

For each aperture: clear/half-rain x positive/zero cache x enabled0/1 = eight
cases. Sun world axis is (0,1,0). Positive cache RGB=(.5,.625,.75), in native
reserved C6 row; all ordinary sky rows and C7 sky rows are black. Zero cache is
an actual separate control draw. SOLAR=(18,17.6,17), radius=.00465. Rain0/.5
changes only rainStrength, not wetness or geometry. Read back queried uniforms,
matrices, samplers/storage, uploaded VBO and every input texture.

Important discovered coupling: positive C6 cache changes incident irradiance
and therefore reflected water scatter as well as the disk. Do NOT set scatter
to zero. On the qualified open-sky branch, isolate solar transmission as

    (C0_positive - C0_zero) - R_legacy*(scatter_positive - scatter_zero)

Use actual observed WR R coefficient and measured scatter, not guessed ambient
or a total-C0 comparison. Require coefficient equality across cache/source
controls and actual legacy application, no opaque receiver, full sky access.
Any wrong-domain/partial replacement is INCONCLUSIVE, not a solar success.

## Rules and gates, fixed before GPU output

The independent CPU rule uses q=(1-cos(theta))/(1-cos(radius)), with
delta=2*sin(radius/2)^2, positive Gauss-Legendre4 x midpoint-azimuth12 nodes.
Solid angle is delta*dq*dphi, radiance=beam/(pi*sin(radius)^2). Do not renormalize
surviving nodes, normalize observed n/v, regularize a singular inverse, add an
eta-squared compensation or multiply weather/source decay twice.

- Numeric component gate: abs2e-6 + rel2e-4*abs(reference).
- CPU selected-point 8x24 versus 12x48 refinement: abs2e-8 + rel2e-6.
- Positive dq moments degrees0..2N-1: absolute2e-14.
- Projected cap irradiance versus perpendicular beam: relative2e-13.
- Retain previous passive C0/depth and coefficient policies without loosening.
- All 5025 disk-ROI inputs must qualify legacy domain. Export actual new-feature
  application separately; finite whole-ROI checks are not all-ROI convergence.
- Selected fixed pixels: (128,128),(132,131),(123,127),(132,135),(132,127),(142,134).
  Use fresh actual inputs; aperture changes make previous offset-vector pins
  inapplicable. No best-pixel selection after data.
- Pure/observer repeats and input identity must be checked. Pure slots5..7 are
  cleared inactive storage, never observations. Malformed/nonfinite evidence is
  INCONCLUSIVE. Numeric failure with qualified central inputs is diagnostic RED.

Only after a genuine central-response STUB RED may the cap helper be written.
Native pixel-filter equivalence and physical/natural adoption stay false even
if the bounded sharp-response gate becomes GREEN. The normal game is cleanly
saved and stopped before root-owned native GL, and restored after all GL ends.
No automatic terrain/time/camera action in the ordinary world.
