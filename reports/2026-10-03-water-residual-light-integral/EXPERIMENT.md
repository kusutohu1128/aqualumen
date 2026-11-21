# Water residual light-space integral — pre-GPU contract

Recorded 2026-10-03, before the new probe's first GPU execution. This is an experimental, unselected pack; no shipping or Minecraft visual acceptance is implied.

## Prior evidence and ranked predictions

The frozen angular packet (manifest SHA256 `675110c0c0b7ff643479a23fdcfafa0e6fc80f5cebe030c852d9a453d73a9700`) and inverse-mapping packet (`0c01317d9376607aee1de03c7bf82699efbb176a4027161e5f680f9c370cafb2`) were rechecked this turn. The previous turn made progress: finite quadrature matched its own double reference, while the narrow-source continuous reference exposed undersampling. It did not establish a visually accepted cure.

1. A small angular light source is undersampled by the existing slope-space GH3 rule. Replacing only its integral, without widening or dimming the source, should recover the qualified reference response.
2. An inverse branch, measure Jacobian, or raw binary32 view-vector discrepancy could invalidate that replacement. Reconstruction and independent CPU checks must remain separate gates.
3. Gain changes, rejected-node renormalization, or disappearing light can make the image look smoother without fixing the integral. They are disallowed; rejected new integration falls back to the complete old helper and reports `applied=0`.

The original seven selected coordinates and five tiny-response INCONCLUSIVE results in the prior packet are not rewritten. The following additional six coordinates, selected in that prior turn, are fixed before this new GPU run. The red-channel targets are from the frozen qualified continuous slope integral; green and blue are exactly one half and one quarter of red for this controlled source.

| Pixel | Red target |
|---|---:|
| 128,128 | 0.008620047860082714 |
| 132,131 | 0.013054451421566662 |
| 123,127 | 0.0032931954429157133 |
| 132,135 | 0.003249341819018176 |
| 132,127 | 0.004662952074109474 |
| 142,134 | 0.0027144296933907888 |

The frozen reference JSON SHA256 is `f8ec3ab6a5e330abdad8e493d913e54f2481a308dc1612fdf1c5106987d9d2c5`. The test harness pins the actual mean normal, raw view vector, covariance, and footprint at these points.

## One changed causal variable

The new wrapper initially calls the complete old helper unchanged: this must produce a genuine same-domain numerical RED, not merely a compile error. Only after that run may the sharp-source integration be implemented. The same compiled probe binary and fixed acceptance targets are used for GREEN. Geometry, wave covariance, GH3 background, Fresnel law, radiance units, source peak, source width, time, camera, and textures stay unchanged.

For the narrow diagnostic, source radiance is the derivative-free chord Gaussian with peak RGB `(0.25,0.125,0.0625)` and sigma `0.00465`. Define `u=chord^2/(2*sigma^2)`, `cos(theta)=1-sigma^2*u`, `sin(theta)=sigma*sqrt(u*(2-sigma^2*u))`. Solid angle is `sigma^2 du dphi`. Positive Gauss-Laguerre radial weights contain `exp(-u)`; the initial GPU rule is 8 radial by 16 azimuth samples. CPU 12x32 and 16x64 refinement is a separate check, not permission to change the fixed reference or gain.

Preserve raw input `v` rather than silently normalizing the legacy caller. With eta=1.333 and normalized outgoing light direction `t`, set `k^2=1+eta^2*(dot(v,v)-1)` and `n=normalize(k*t+eta*v)`. Require the correct water-facing branch, positive facing, no total internal reflection, and reconstructed legacy `refract(-v,n,eta)=k*t`. The slope-to-solid-angle Jacobian is `k^2*abs(dot(t,n))/(length(k*t+eta*v)^2*abs(n.y)^3)`. The integrand multiplies the unchanged Gaussian slope density, legacy projected weight, and legacy `(1-Fresnel)` transmission. This is a change of variables for the retained renderer model, not a claim of a complete physical BSDF or an added eta-squared energy factor.

Radial quadrature and change-of-variable references: [NIST quadrature](https://dlmf.nist.gov/3.5), [PBRT rough dielectric measure discussion](https://www.pbr-book.org/4ed/Reflection_Models/Rough_Dielectric_BSDF). The retained renderer differs from PBRT; these references do not certify it.

## Qualification and negative controls

`WLS_status=(requested, applied, sourceKind, rejectionCount)`. `applied` means the new integral was actually used. SPD covariance and supported sharp source are required. Zero or rank-deficient covariance is unsupported and preserves the old helper, with no epsilon inverse. Any invalid sampled new node rejects the entire new integral; no node deletion, partial-energy return, or survivor renormalization.

The unchanged 5025-pixel common core ROI must satisfy the original legacy domain guards. Candidate narrow-source `applied=1` is required on the entire ROI; control and broad, constant, and dark sources require `applied=0`. A valid legacy domain with narrow-source `applied=0` is a functional RED, not an INCONCLUSIVE success. No post-hoc ROI reduction.

- Six-point output RGB: absolute `2e-6` plus relative `2e-4` against the fixed continuous reference.
- Observer passivity: C0 absolute `5e-4` plus relative `2e-4`, depth `2e-6`.
- Current normal, view vector and scatter XYZ comparison: `EPS8=8*2^-23`; alpha, eligibility, covariance, footprint, flags, depth, textures, matrices and declared inputs remain exact where applicable.
- Retained coefficient comparisons: `2e-5`. Broad/constant/dark must preserve the old output under the declared EPS8 construction/passivity boundary, not a loosened alias gate.
- Pure output, repeated output, observed output, repeated observations, expanded shader sources and actual queried input values are retained. Source seam recovery must match the frozen guard baseline and resolved parent, not just a textual resemblance.

The Gaussian integration does not establish native solar-disk radiometry, all-tail visibility, critical-angle behavior, screen-rim stability, temporal motion, or actual Iris acceptance. Those remain separate required steps before adoption. Existing slope-reference finite-domain/tail bounds remain recorded in the prior packet; no global visibility bound is inferred from a finite set of light nodes.

Additional implementation guard recorded before the new probe's first GPU run: binary32 inverse reconstruction uses componentwise `EPS8*max(1,k,eta)`; the double CPU inverse retains its `1e-11*max(1,k)` guard. This is an arithmetic guard, not a universal error proof. Native source kind0 is deliberately unsupported by the first candidate and remains full legacy with `applied=0`; only diagnostic kind1 can use the new integral. A small removable bridge after the unchanged old helper reads its applied status, preventing an added source term on a legacy fallback. Existing implicit depth/color lookup traces are preserved; the test's NEAREST, base-level-only, open-depth inputs do not establish general Iris derivative or receiver safety.

## Root-only native lifecycle

The ordinary world was saved through the menu; all dimensions' save messages and a separate fresh title screenshot are retained. The ordinary launcher exited normally. Configuration snapshots and a fresh post-save comparison copy are in a private cache and must never be restored over user saves. All Minecraft JVMs are absent before native GL. Agents are CPU-only.

The retained `make check` passed on the RTX 3080 Ti before the new probe. After all native GL work, verify unchanged ordinary configs and save identity, launch the unchanged selected 0.6 pack with the normal account and physics 0.2, capture a fresh paused screenshot, and do no further GL work while the game is running. No test pack is installed by this experiment.
