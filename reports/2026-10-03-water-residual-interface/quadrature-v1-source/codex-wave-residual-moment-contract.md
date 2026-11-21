# Wave residual moment contract

2026-10-03. Isolated CPU/source slice; no GL/GPU execution, production hook,
pack installation, rendering acceptance or benchmark. The new
[helper](../../shaders/lib/wave_residual.glsl) is a TEST building block for
[the physical follow-on](codex-resolved-normal-physical-next.md), not adoption
of the normal cutoff or an implemented physical BSDF.

## Public interface and source contract

`vec3 waveResidualCovariance(float footprint,float depth)` returns
`(Cxx,Cxz,Czz)` for the symmetric XZ **slope** covariance, not unit-normal
covariance or scalar roughness. Caller includes production settings and
`waves.glsl` first. The helper invokes the original `waveMode`; it does not
copy a mode generator, add includes, evaluate phase, use samplers, or change
production callers. Inputs require finite nonnegative footprint and finite
depth with the current finite spectrum/settings.

For each original mode, use
`G=1-smoothstep(2,5,k)`, `B=exp(-.25*(k*footprint)^2)` and `f=G*B`.
With the same full-spectrum normalization as production,
`a=.5*WAVE_HEIGHT/sqrt(max(sum(.5*weight^2),1e-6))`, and the same
`s=smoothstep(.035,.8,depth)`, the returned matrix is
`sum((1-f^2)*.5*(a*s*weight*k)^2*(d d^T))`.
Normalization does not depend on G or B. Squaring the shore factor matches
the height/slopes' spectral attenuation. No extra pixel-loss scalar is added.
In exact arithmetic this weighted dyad sum is positive semidefinite; xz can
be negative. GPU rounding/PSD tolerances remain unqualified.

## Statistical limit

This is an **independent-phase, independent missing-power moment closure**.
It is not the exact residual obtained by subtracting the soft resolved field
from the same deterministic modes. Let `M=.5*(a*s*weight*k)^2*(d d^T)`.
That split has resolved moment `f^2 M`, residual `(1-f)^2 M`, and
cross-covariance `f*(1-f) M`; full moment includes twice the cross term.
The proposed replacement `(1-f^2) M` retains missing total ensemble power
only by a declared independent replacement assumption, not by proving the
conditional surface distribution.

The first accepted modeling domain must be known/deep, zero bathymetry
gradient and zero interaction ripples. Depth taper is included algebraically,
but shallow-water product-rule gradient covariance, ripple covariance,
final-normal derivative variance, grazing modification and visibility are
excluded. The helper has no inputs to recover those terms. A covariance does
not define distribution tails, masking/Smith visibility, energy/reciprocity,
offscreen geometry or fluid conservation.

## Retained CPU/source checks

One source-contract tracer ran RED before creation (`FileNotFoundError` for
the public helper), then the same check ran GREEN after the minimal helper.
Subsequent static guards verified the exact transfer/normalization/dyad source,
original `waveMode` dependency, and no other shader references at that check's
snapshot. These are source guards, **not execution of GLSL**. There are no new
test/report files in this ownership slice.

Independent CPU closed-form identities used WAVE_HEIGHT=.12 and normalization
above its floor. A single mode then has full slope power `(.12*k/2)^2`.
The checked `(xx,xz,zz)` expectations were:

| Independent case | Expected covariance |
| --- | --- |
| k=1, G=1, footprint0, direction X | (0,0,0) |
| k=5, G=0, direction X | (.09,0,0) |
| k=3.5, G=.5, footprint0, direction X | (.033075,0,0) |
| k=1, G=1, footprint=.4, direction X | (.000276781153008111,0,0) |
| k=5, direction (1,-1)/sqrt2 | (.045,-.045,.045) |
| Equal-weight orthogonal k=5 modes, shared normalization | (.045,0,.045) |
| k=5, direction X, shore=.5 | (.0225,0,0) |

All checked dyads/sums satisfy PSD up to the declared CPU algebra tolerance
`1e-16` on the determinant. For the taper case, full=.0441, resolved=.011025,
exact omitted-field moment=.011025 and cross=.011025; `.033075` is omitted
plus twice cross, not omitted alone. These synthetic modal algebra checks do
not validate native production `waveMode` numerics or the GLSL helper's output.

Root must establish actual shader-main covariance observations, zero-residual
matching-mean recovery and distribution/Fresnel/TIR source-response regressions
before native model acceptance. No GLSL compile/link or render test was run here.

Pinned helper SHA256:
`9a481ce20b3f5301640b36607f6ce883f0625433b534d29b802bf806bf47ccf0`.
Unchanged production waves SHA256:
`4fc71a62459fde55261a68217d4d18d715cd2b678274af1b6c8812ebd3153191`.
