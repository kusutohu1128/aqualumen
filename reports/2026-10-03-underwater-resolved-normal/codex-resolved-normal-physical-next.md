# Resolved surface and residual interface: next physical slice

2026-10-03. CPU/source design only: no shader implementation, GPU/game run,
live-pack change, or adoption of the detail0 cutoff. This follows
[the fixed-density assessment](codex-fixed-density-result-next.md); the cutoff
remains a causal diagnostic, not a physical fix or accepted appearance.

## Source gap, not a proved cause

[VS](../../shaders/gbuffers_water.vsh) and fixed-density TES use detail0,
footprint0 height. [FS](../../shaders/gbuffers_water.fsh) normally uses detail1
slopes with `max(1.25*footprint,.035)`. The diagnostic changes only known
underwater upper-interface detail. Ripples, orientation/grazing, variance and
transport laws remain separate. Subdivision does not restore discarded modes.

[waves.glsl](../../shaders/lib/waves.glsl) supplies a scalar pixel-discard
variance, not geometric-discard variance or directional covariance. Underwater
FS samples transmitted sky through one normal; its roughness-filtered reflected
sky and scalar-roughness solar lobe are air-side only. TIR reflection sees
water/scatter or an SSR receiver, **not air sky**. Exact interface Fresnel in
[water.glsl](../../shaders/lib/water.glsl) does not make those approximations a
complete rough dielectric BSDF. Its above-water Smith-GGX Sun lobe is not an
underwater masking/visibility model.

## Declare the missing variance policy first

For a uniform deep column, let normalized full modal height amplitude be `A_i`,
direction `d_i`, wavenumber `k_i`, and optical transfer `f_i=G_i B_i`, where
`G=1-smoothstep(2,5,k)` and `B=exp(-.25*(k*footprint)^2)`. Geometry uses G;
the optical mean additionally averages the footprint. Under an explicitly
assumed independent-phase ensemble, define the slope moment matrix
`M_i=.5*A_i^2*k_i^2*(d_i d_i^T)`.

For the deterministic soft split of the same waves:

- Resolved covariance is `sum(f_i^2*M_i)`.
- Full-minus-resolved covariance is `sum((1-f_i)^2*M_i)`.
- Resolved/residual cross-covariance is `sum(f_i*(1-f_i)*M_i)`.

Thus full covariance includes twice that cross term. The simpler nonnegative
`sum((1-f_i^2)*M_i)` is an **independent missing-power moment closure**, not
the exact covariance of the omitted deterministic field. Recommend this as a
clearly labeled first TEST closure, not a claim of conditional physical truth.
A hard disjoint spectral split avoids that overlap but changes the mean model
and belongs to a different experiment.

Replace bookkeeping from one declared transfer, rather than adding a geometric
loss to the existing `1-B^2` scalar: that can double-count. Do not add residual
variance around an unchanged detail1 normal. Retain the directional xx/xz/zz
matrix and validate positive semidefiniteness. Shallow-water product-rule terms,
nonzero bathymetry gradients, interaction ripples, and final-normal derivative
variance need their own consistent accounting; exclude them from the first
fixture instead of silently assigning them independent variance.

## Minimum operator slice

Use the same fixed geometry and phase in both programs. First domain: known,
deep, open upper interface, uniform column, zero ripples/gradient, no opaque
receivers, zero C8/Sun/Moon/foam, and inactive grazing modification. Preserve
unknown, side, bottom and air-side production paths as negative controls.

Evaluate a common resolved slope plus declared residual-distribution samples.
Covariance alone does not specify a distribution or its tails: declare the
distribution approximation and positive, normalized quadrature/refinement
policy before coding. For each normal, evaluate Fresnel, TIR, and reflected/
refracted directions **before** evaluating directional radiance and averaging.
Do not average normals or Fresnel first. Underwater transmitted rays use the
air-sky source; reflected rays use the water-side source. A separate mirrored
air fixture can qualify reflected-sky integration without inventing underwater
sky reflections.

Reject the initial fixture if quadrature normals become hidden/backfacing;
do not flip them or renormalize surviving weights to conceal missing mass.
Finite valid nodes are not proof about distribution tails. Visible-normal
measure, projected-area weights, masking/shadowing and reciprocity are later
required work, not implicitly supplied by this quadrature. Avoid applying the
old angular sky blur again to the same residual. Sun/Moon coverage derivatives
must eventually remain outside divergent per-ray branches, with their angular
filter and solar lobe double-counting separately tested.

## Establish the actual-main regression seam before implementation

[glcheck.cpp::underwaterSkyProbe](../../tools/glcheck.cpp) already exercises
production water main with directional LUT tags, unrelated camera colors,
independent flat Snell/Fresnel expectations, TIR, opaque and dark-cave controls.
[The angular harness](../../tools/underwater-angular-probe.h) offers original
main observation and source-response tests. Reuse those real call sites with
the actual VS/TCS/TES/FS, matrices and sampler inputs; a helper-only Fresnel test
cannot qualify this operator.

First qualify removable final STORE observations: byte-identical recovery,
passive C0/depth neutrality, repeats, and saved immutable inputs. Observe actual
resolved n, covariance, quadrature mass, reflected/transmitted coefficient sums,
TIR mass and receiver/source classification alongside C0. Then retain a failing
nonzero-residual directional-response test at that seam before model code.

Keep two zero controls distinct. A disabled TEST hook must literally recover
the unchanged production path. A physical zero-residual fixture must also have
matching mean normals, e.g. WAVE_HEIGHT0 and no other slope source. With nonzero
discarded modes, detail0 mean plus zero covariance cannot equal production's
detail1 normal. Check covariance→0 continuity with the **same mean**; do not hide
a discontinuous bandwidth switch behind an exact-zero bypass.

Use separate constant R/T source tags to test nonnegative finite weights,
`sum(w)=1`, `sum(w*F)+sum(w*(1-F))=1`, and no TIR transmission. These establish
coefficient conservation, not physical radiance/flux conservation. The existing
eta-squared correction is restricted to one known C8 direct component; it is
not permission to scale all sky/scatter. Declare medium radiance units,
projected measure and angular/eta mapping before an energy or reciprocity test.

Next sweep incidence densely across the critical angle with constant sources,
then directional LUT patches; require Fresnel→1, transmission→0, no safe-ray
leak, and convergent quadrature refinement with tolerances fixed before GPU.
Retain camera-color independence, opaque/dark-cave negatives and source angular
filter uncertainty. Native acceptance still does not prove Iris bindings,
same-frame images, Minecraft primitive counts, visual adoption or frame time.

The next deliverable is this bounded test/closure contract, not full fluid
conservation, physical self-occlusion or offscreen object reconstruction.

Source snapshot: FS `8dfae28a5a98d5c9be4a0e39488cdfe66a01440d2123fd786e83e3e3fcfc0b18`;
waves `4fc71a62459fde55261a68217d4d18d715cd2b678274af1b6c8812ebd3153191`;
water `e9e6ac73ca6c451907e8f515913898b000e494c55947cd5e2f44d05db3d65b39`;
glcheck `fc186ee670aeadd94a4186669aaf518f6d80ee9c2c8ce103e09a68a708712e16`.
