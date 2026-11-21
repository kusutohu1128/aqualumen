# Enabled1 near: bounded saved-data rejection diagnosis

CPU/source-only diagnosis. No shader, gate, model, coordinates, geometry,
scattering, installed pack, game or frozen packet was changed. The existing
public saved-file audit was replayed and still exits1 with
`NEGATIVE_INSUFFICIENT_APPLICATION`: requested16, applied2, rejected14; the
predeclared minimum4 is unchanged. This reproduces the telemetry failure, not
the screenshot's appearance or motion.

The two applied coordinates are (801,451) and (801,251). Every other fixed
coordinate has status `[1,0,0,48]`. All16 have the same covariance
`(0.006807451602071524,0.0027949956711381674,0.002802651608362794)` and flags15.
Its determinant is 1.126691437971654e-5 and Schur remainder
0.0016550854913589088: this saved covariance is strictly positive definite,
not rank/zero. Coefficient maximum mass error is 2.384185791015625e-7 and
R+T balance error1.7881393432617188e-7. TES maximum alpha error is
5.960464477539063e-8 and barycentric sum error1.3969838619232178e-7.

## What rejection48 already distinguishes

Pinned CAP helper `shaders/lib/water_residual_sun_cap.glsl` SHAa0708a5d...196c3:

- Lines33-53 set request and candidate; lines68-71 return an absent/invalid
  candidate with rejection0 or1, never48.
- Lines58-73 run both old full/base calls and require their application and
  finite colors before entering the node loop at90. If this fails, final
  fallback148 supplies rejection1, not48.
- Each failed node increments rejection once and continues at100,107,114,
  128 or140. Although `valid` becomes false, the entered loops keep visiting
  later nodes; there is no survivor normalization or early loop break.
- Thus, under the verified source contract, rejection48 is evidence that a
  candidate entered the cap node loop with both old results applied/finite,
  and all48 nodes failed a node gate. It is not a fresh generic GL invocation
  count query, an all-world proof, or a direct WR_status readback.
- Final fallback146-149 returns saved full legacy color. Covariance/coefficients
  remain old-helper output; their presence does not identify which node gate
  rejected. Zero source, world authorization, rank/zero covariance and merely
  unapplied old calls do not explain this specific48 pattern.

## Ranked falsifiable hypotheses

1. **World-hemisphere restriction, especially reflected.y>=0 at113.** Inverse
   solar facets can transmit an upward solar direction but reflect above the
   mean interface, which this deliberately restricted slice rejects. It
   naturally predicts a small central accepted region and peripheral failures.
   For the illustrative exact-unit view v=(sin(theta),-cos(theta),0), zenith
   target t=(0,1,0), eta=1.333, and D=1+eta^2-2eta*cos(theta), the inverted
   facet has reflected.y=[2eta-(eta^2+1)cos(theta)]/D. Hence reflected.y<0
   requires theta<16.246451520784824 degrees; merely facet.y<0 permits
   theta<41.39337360830972 degrees. This is an analytical example, NOT an
   actual reconstructed angle, native Sun axis, FOV, or physical self-occlusion
   proof. Prediction: a reason-only observer reports hemisphere failures at
   the rejected points, while the two applied points report no failures.
2. **Wrong/critical inverse branch at105-107.** Farther view directions can
   violate facet.y<0, facing>0, transmittedDot<0 or positive discriminant.
   Prediction: the branch/critical category, not receiver category, accounts
   for the first failed node and all rejection counts in those points.
3. **Opaque screen-space receivers at139-140.** The48 closely clustered cap
   rays can all hit a bank/opaque reflector even when the nine different old
   GH3 facets did not. Prediction: kind1 or reflection.a>0 is exported after
   all preceding node tests pass. In production FS, refraction kind1 means
   converged opaque receiver (126-177); reflection positive alpha means a
   refined opaque hit (27-100). Offscreen/unknown kind0 alone is NOT rejection:
   the cap accepts it with skyAccess^2 fallback.
4. **Raw-vector inverse reconstruction/finite arithmetic at111-114.** The
   raw-v k2 correction and finite EPS8 bound are preserved, but near-critical
   cancellation could exceed the bound. Prediction: reconstruction/finite
   failure with direction/hemisphere passing. Saved raw mean n, v, Sun axis,
   per-node discriminant and reconstruction error are absent, so this cannot
   be numerically tested from the current sixteen C9..12 records.
5. **Kernel finite/nonnegative validation at124-128.** Lower priority given
   the shared well-positive covariance, but mean-slope-dependent arithmetic
   is not recorded. Prediction: this category dominates only after inverse
   and hemisphere tests pass. A tiny Gaussian density or underflow to zero
   alone is allowed (density>=0 and kernel>=0), not a configured cutoff and
   not an explanation for rejection48 without a failed guard.

The old CPU `light_kernel` in `tools/water_residual_light_integral.py:144-178`
uses the same inverse/facing/critical/reconstruction/downward-reflection
contract. That source agreement is not a replay of actual Iris vectors.

## One next test: passive first-failure-category observer

Propose one separately approved TEST-only observation experiment, not a fix.
Generate a temporary instrumented copy of the exact a070 helper with removable
diagnostic tags; do not edit its frozen/live bytes. Keep every existing
predicate, arithmetic expression, loop bound, call, return, threshold and
all-or-nothing fallback byte-identical after tag removal. Record mutually
exclusive first-failure categories at the five existing failed-node branches,
splitting line114's hemisphere predicate from reconstruction/finite failure,
and line140's opaque transmission from opaque reflection. Use already computed
values only; do not add derivative calls, change control flow or normalize n/v.

A new authoritative reason-only observer may replace C9's diagnostic payload
with `(firstReason,hemisphereRejectedNodes,receiverRejectedNodes,otherRejectedNodes)`;
C10 WNS status, C11 covariance/original flags and C12 TES stay unchanged.
It must not be fed to the current coefficients auditor or mislabeled as old C9
coefficients. An explicit integer category legend and deterministic priority
are required. The node-category count sum must equal the existing rejection
count for loop-entered records; otherwise the new observation is inconclusive.

First public CPU tracer test: removing these diagnostic tags and STORE recovers
the pinned physical helper/FS exactly; synthetic category accounting rejects
missing/mislabelled categories. Root then performs native same-main physical
versus reason-observer C0/depth/repeat neutrality using existing declared gates
before any installation. Finally observe the SAME fixed16 coordinates in the
same guarded near scene, retaining the unchanged minimum4 application verdict.
No shrinking ROI, choosing successful coordinates, relaxing hemisphere/receiver
guards or claiming that diagnosis is model/AA/shipping acceptance.

## Limits and image separation

The current metadata exports no actual per-point raw n/v/Sun vectors or reason
code; coefficients are not WR valid/applied telemetry. Flags15 is original
eligibility, not authorization/application. Guard int1 is a separate prepared
uniform observation; FINAL-bound samplers are another observation. Their
matching frame numbers13279 do not establish the exact same draw, fragment
fetch, screenshot frame or node execution trace. The central blob/smaller
sun-point appearance described by root is separate visual evidence, not a
proved cause derived from these later records. No all-six-view Iris PASS,
physical correction, pixel-AA equivalence, narrow-SPD/critical/visibility,
energy/reciprocity, motion, general performance or shipping acceptance follows.

The diagnose skill's feedback-loop phase was limited to replaying the existing
saved-file audit. Instrumentation/fix/cleanup phases are intentionally deferred
under the read-only, no-GPU task authority; there is no implemented fix claim.
