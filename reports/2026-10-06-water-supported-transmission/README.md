# Supported rough-water transmission: implemented CPU reference

Status: **concrete optical-model implementation progress, not a shader fix**.
The previous goal turn established the actual legacy admission/input seam and
native observation passivity. This turn implements the independent source/
visibility reference needed for the next actual-MAIN optical RED→GREEN.
The full realism objective in `docs/REALISM_GOAL.md` remains active/unachieved.

## Model and provenance

Inputs are the four unchanged actual Iris phase45 full records from the sealed
[legacy-branch cycle](../2026-10-06-water-legacy-branch/README.md), copied exactly
to `actual-iris-inputs.json`. Raw n/v/C are never repaired or normalized.
Eta is the actual binary32 value `1.3329999446868896`.

The declared model integrates **unit constant upward air radiance**, with black
water reflection, over a correlated Gaussian world-horizontal projected-area
slope distribution. It preserves the old source-unit convention; no eta-squared
radiance/beam calibration is silently added. Unsupported/backfacing/critical
directions contribute zero **individually**, not a global fallback. Both world
air hemisphere and opposite tilted-macroplane hemisphere support are explicit.

Masking/shadowing uses a height-correlated Smith statistical closure, NOT actual
intersection with unresolved water geometry. For Gaussian slopes, the projected
area numerator `q=side*(w_y-w_x*s_x-w_z*s_z)` is Gaussian. With mean magnitude
`D`, standard deviation `sigma`, and `a=D/sigma`,
`Lambda=phi(a)/a-Phi(-a)`, and the declared bidirectional factor is
`1/(1+Lambda(view)+Lambda(light))`. Directional variance retains covariance xz.
This follows from the visible-area constraint, not post-hoc normalization of
surviving light samples. The numerical one-direction visible-area identity is
separately tested. Macro-grazing Lambda is infinite, giving zero visibility.

Primary algorithm references: [PBRT masking/shadowing](https://www.pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory)
describes the projected-area constraint and height-correlated approximation;
[Heitz's masking-shadowing analysis](https://jcgt.org/published/0003/02/03/paper.pdf)
discusses Smith/Gaussian behavior. The correlated, tilted-world-slope expression
above is our explicit derivation from the project's Gaussian measure. No copied
shader-pack or PBRT implementation code, purchased assets or GGX substitution.

Important bounds: strict positive-definite C only; zero/rank-one residual,
reflection, opaque receivers/caves, varying sky/Sun, arbitrary wet geometry,
multiple scattering and physical radiance/energy/reciprocity remain uncovered.
This is not mass-conserving fluid simulation or a complete rendering model.

## Two independent integration domains

`tools/water_supported_transmission.py` implements both:

- Forward Gaussian slope-domain Fresnel/refraction/support evaluation.
- Inverse air-direction evaluation, retaining raw-view outgoing norm and the
  slope/solid-angle Jacobian. The inverse critical cosine is computed from
  `-k*dot(target,facet)` to avoid subtractive loss close to critical incidence.
  Reconstruction tolerance is unchanged; no normal flips or epsilon repair.

Light integration splits the supported azimuth arcs and macroplane horizon.
The independent forward integration partitions slopes at analytically derived
quadratic critical/horizon roots, using forward branch evaluation for inclusion.
Squaring can introduce extra roots, but not extra accepted contributions. A
cosine quadrature-coordinate map handles endpoint behavior without modifying
optical functions. The finite8-sigma square retains original density; its
omitted absolute-response tail is bounded analytically below `4e-15` here.

The final [reference-v4](reference-v4.json) uses light orders48/64/96 and forward
split orders96/128/192. All4 points pass the **predeclared, unchanged**
`2e-6+2e-4*max(response)` cross-domain/refinement gate. Cross-domain differences
are at most `1.68e-14`; light refinement at most `5.75e-9`.
These are strong numerical agreement/refinement checks, **not rigorous interval
quadrature enclosures**. The positive lower estimates are not certified lower
bounds; the earlier v2/v3 field name is superseded by explicit v4 semantics.

| Actual source coordinate | Model air transmission response |
| --- | ---: |
| 1114,181 | 0.0654691768 |
| 1114,169 | 0.0425856765 |
| 1114,155 | 0.0244136123 |
| 1114,151 | 0.0205989004 |

Thus this declared continuous source/visibility model retains positive air
response at the actual input where the legacy operator rejects everything.
That supports the next falsifiable MAIN source-response test. It does not itself
establish an actual shader source-control difference or full-frame band causality.

## Retained failures and tests

- Stub RED:3 failed tests/1 error; archived original stub. Not a GPU/optical RED.
- Initial model's5 arithmetic tests pass. Full-domain reference then fails the
  inverse reconstruction check near critical incidence; v1 empty output/log kept.
- Dedicated critical test fails; stable inverse formula yields6 tests GREEN.
  Reconstruction/unit tolerances are not widened.
- v2 unsplit forward256/384/512 grid fails refinement at two selected inputs.
  Those records remain INCONCLUSIVE; the acceptance gate is not relaxed.
- Analytic support partition/cosine map yields v3/v4 all4 qualification.
- Final9 tests pass, including input rejection, supported/absent directions,
  near-critical reconstruction, analytic partition vs5,005 independently sampled
  forward classifications, visible-area identity and finite-difference Jacobian.
  The forward/inverse test is one selected supported node, not every node.

These are CPU results only. No new GLSL, native GPU, Minecraft benchmark, live
TEST installation or actual-MAIN optical RED→GREEN ran this turn. No visual,
motion, physical-energy or ordinary-release adoption is asserted.

## Runtime and next implementation

Normal0.6/physics0.2 remains selected with exactly the three ordinary active JARs.
No world/config/terrain/camera/time changes or save restoration occurred this
CPU-only turn. Root polled the same owned launcher handle12444, then freshly
inspected F2 `ordinary-still-paused.png` at11:17:12 JST. No native GL work occurred.
The sealed prior1685 files still verify. Tracked dirty-diff SHA stays
`ee4e019473a0468d187e9d3567ec1b1e30f4c6a5dc6b0526c494c3dcbfdd52c5`.
Pre-existing OpenAL failure is unchanged; no audio repair was attempted.

Next: implement the supported operator in reversible TEST GLSL and turn the
matched original-MAIN source-control seam into an actual OLD RED/candidate
GREEN. Preserve independent positive/zero-source controls, correct reflection/
transmission handling and declared units. Do not substitute additive tag injection
alone for fixing the interface operator or merely remove the rejection guard.
Then retained GPU regressions, actual near/deep/tilt and moving views must pass.
This model reference narrows that implementation; it does not replace broader
shore/cloud/day-weather/transport/contact/motion work or full-goal acceptance.
