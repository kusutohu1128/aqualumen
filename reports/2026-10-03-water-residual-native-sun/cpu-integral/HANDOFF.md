# Native sharp-Sun CPU source integral

READY/frozen source `tools/water_residual_sun_integral.py` SHA256:
`d58d86873b192f6015ce0ae50c2dbce4d0ac839d6feb603685ddde217df8de1e`.
Public tests SHA256:
`834a5c8c41abda155ed074b589ad1a4a7bfa8346ed7e1ef57f6e5f67088b1e99`.

Two behavioral CPU RED→GREEN verticals were retained: an off-axis cap's
projected irradiance versus its once-weathered beam, then a positive resolved
water response distinct from zero or a point-cap approximation. Four public
tests pass, including positive moment preservation and whole-source rejection
for unsupported covariance. No missing-module failure is labeled behavior RED.
No GL, game, native binary or shader execution was performed by this agent.

## Public seam and rules

`solar_beam(cached_transmission, rain)` applies `SOLAR=(18,17.6,17)` times the
provided cache times `(1-.85*rain)` exactly once. The cache is not recalculated
or multiplied by another cloud/weather factor. No eta compensation is added.

`sun_integral(fixture, sun_direction, beam, radial_order=4, azimuth_order=12)`
accepts fresh raw `mean_normal`, `view_to_eye` and `covariance`. Only the
generated Sun axis is normalized. The existing public raw-v `light_kernel` is
hash-pinned to `f5b6db7013907ab4baf6e28df0542a2f2066ddaef1c8cdb6e8a28fc4e352de92`
and is not modified or monkeypatched. Every finite cap node must pass that
kernel's existing inverse/Fresnel domain; an invalid node rejects the entire
returned source, with no deletion or surviving-node renormalization.

The cap radius is .00465 radians, `delta=2*sin(radius/2)^2`,
`q=(1-cos(theta))/delta` on [0,1], `cos(theta)=1-delta*q`, and
`sin(theta)=sqrt(delta*q*(2-delta*q))`. Solid angle is `delta*dq*dphi`.
Radiance is `beam/(pi*sin(radius)^2)`; perpendicular irradiance integrates
back to beam. The cap uses an orthonormal basis around arbitrary source axis,
matching the atmosphere basis-axis convention. Positive GL4 ×12 midpoint
azimuth is the candidate; GL8 ×24 and GL12 ×48 are separate refinements.

`gauss-legendre-cap-rules.json` SHA256:
`4cae55d8c6d33b65d8aab0c2ced84a051151e889b08d9ee54c8dd4dc89318787`.
Moments degree 0 through 2N-1 have maximum absolute errors 2.22e-16,
5.55e-17 and 2.22e-16 for N=4,8,12 respectively; declared gate 2e-14.

## Pre-GPU reference results

The unchanged six previously saved binary32 vector fixtures are used as CPU
fundamental cases, plus an explicitly synthetic normal-incidence/up-Sun case
with the observed covariance. These are not newly captured native-Sun vectors.
An initial report uses synthetic unit transmission/no rain; it is preserved as
`seven-sharp-sun-reference.json` SHA256
`f3de7979ca0aad511afb05602ef6953f412948491fa360575d55783ac7779cd3`.

Root's declared native fixture inputs are cache(.5,.625,.75), Sun(0,1,0):

- Clear rain0: beam(9,11,12.75), reference SHA256
  `8b8917f83d95f5f348f64112223ef3b6f4c2db11f15f7a41781ccb8571af841f`.
- Rain.5: beam(5.175,6.325,7.33125), reference SHA256
  `ea65f42f563ee01da93a3b567d10347b09ad3c31398967bdbc43aa7d20ba2ff7`.

All seven cases pass each report. Before evaluating these references, gates
were declared and approved: candidate4×12 versus refined12×48 component
`abs2e-6 + rel2e-4*max(abs(a),abs(b))`; refinement8×24 versus12×48
`abs2e-8 + rel2e-6*max(abs(a),abs(b))`; projected beam units relative2e-13.
No gate was changed after results. For the clear native fixture, maximum
candidate/refined C0 difference is 2.887645678129047e-11; maximum refinement
difference is 1.8189894035458565e-12; maximum projected-beam relative error is
3.2297397080004555e-16. Fresh driver inputs can be passed to the same API;
old vector pins are not mandatory for a later native audit.

CLI examples:

`python3 -B tools/water_residual_sun_integral.py --export-rules NEW-RULES.json`

`python3 -B tools/water_residual_sun_integral.py --cache .5 .625 .75 --rain .5 SAVED-ORACLE.json NEW-REPORT.json`

## Explicit boundary

This is finite sharp-source integration and local CPU convergence/units only.
It is not equivalence to the derivative-filtered screen-pixel
`solarDiskCoverage`/`sunDisk` signal. It does not establish a global visibility
or receiver policy, near-critical/singular limits, full physical flux/energy,
reciprocity, native execution, Iris appearance, motion/FPS, or shipping adoption.
The original raw-v optical kernel and IOR1.333 are preserved; no new Fresnel,
geometry, covariance or source gain was introduced. Existing production,
helpers, previous CPU tools and frozen packets remained untouched.
