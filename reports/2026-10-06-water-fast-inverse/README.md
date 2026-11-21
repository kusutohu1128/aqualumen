# Same-model inverse and probability-panel quadrature

2026-10-06 JST. Concrete TEST implementation and actual NVIDIA/original-MAIN
progress, **not** an accepted natural-water renderer or completed realism goal.
No new pack, Mod or TEST configuration was installed. Normal shipping selection
remains0.6/physics0.2. All prior sealed failures and dirty work are preserved.

## What changed

1. Inverse-only fast64 replaces the selected conditional Gaussian inverse with
   independently generated Chebyshev inverse-erf ratios. Own coefficients come
   from Python NormalDist, not a copied library/shader pack. The idea of the
   inverse-erf variables is referenced to
   [Mike Giles](https://people.maths.ox.ac.uk/~gilesm/codes/erfinv/).
   The same support/CDF masses, proposal inputs, n/v/C/index, Smith/Fresnel,
   source adapter, units and48-node Sun/Moon caps remain. Numerically uncertain
   inverses reject the whole estimate instead of masquerading as absent light.
2. A separately measured change integrates **each analytic support panel** in
   endpoint-smoothed probability coordinates. The map is
   `u=(1-cos(pi*r))/2`, with its original Jacobian and known Gaussian panel mass.
   No survivor fitting, covariance change, source-response fit or gate relaxation.
   CPU-generated x coordinates are declared; GPU computes conditional z. Order8
   is NOT64 total rays: the two selected MAIN contexts use64 T and128 R calls;
   one retained CPU context has80 T. Multiple support panels are counted.

Both are unused in shipping. Original four linked geometry stages and actual
LUT/cache/C4/depth/source queries are retained in NEW packets. A native seam at
one evaluation pixel is only a TEST seam, never a proposed production cutoff.

## Evidence and limits

- Independent standalone port audit:3904 selected scalar gates/16 negatives pass.
  Gaussian quantile port:252 selected gates/4 invalid probabilities pass;
  max absolute error1.0967e-6 against the predeclared2e-6 gate. This is selected
  floating-point evidence, not an interval-certified exact Gaussian inverse.
- Fast64 actual MAIN:10 source cases,920 exact raw comparisons; finite-proposal
  and cap replay pass, **dense coefficient convergence still fails**. Its
  diffuse error9.2433e-5 exceeds6.8827e-6. Speed does not fix sampling bias.
- Probability8 CPU: four saved actual-Iris n/v/C contexts meet all unchanged
  constant-source T/R gates at order8. Order4 fails all eight gates. Orders12–32
  and actual node counts are preserved in `probability-rule-4to32-v1.json`.
- Probability8 actual MAIN: independent replay of10 conditions/920 comparisons
  passes; actual diffuse T error5.38855e-7 <6.88272e-6 and wide-opaque T
  error7.55059e-7 <7.96565e-6. Dense reference is recomputed from each ACTUAL
  n/v/C/eta, not substituted from a different context. The genuine saved
  optical RED and implemented GREEN are `probability-main-optical-{red,green}.log`.
  Zero/source/cave/rain/Moon/invalid/strict fallback and geometry/depth/passive
  controls survive. This is two selected dense coefficients, not arbitrary
  directional-source, critical-boundary or reflection-energy convergence.
- Actual tilted reflector remains positive and black-tag negative in both new
  paths; each independent audit verifies113 raw comparisons. Fast64 sees48 hits/
  16 misses and green0.0732696131; probability8 sees40 hits/88 misses and
  green0.0734698102. Against the retained dense green0.0729541704, probability8
  is about0.707% high: **source-boundary convergence is NOT accepted**, even
  though the constant-source coefficients improved. Miss/scatter/access proxies
  remain explicitly counted, not physically observed offscreen geometry.
  Increasing to order12 gives91 hits/197 misses and green0.0680684820,
  approximately6.70% below the retained dense value. This refinement makes the
  object-source response WORSE; simple higher order is not a convergence fix.
  All113 raw controls still pass, which does not waive this optical failure.
- Native regression suite:11 program pairs compile/link and all retained
  production tests pass on RTX3080Ti, GL4.6 NVIDIA580.173.02. No new candidate
  Minecraft/Iris activation, visual, motion, full-frame or FPS acceptance.

## Draw-only cost, never Minecraft FPS

Both actual same-session ABBA packets retain48 positive GL_TIME_ELAPSED intervals,
six warmups, exact source/input/geometry witnesses and queried attached stages.
They exclude clear/readback/compile/setup. Evaluation is one TEST pixel in a
257x257 draw; no per-pixel/full-frame extrapolation is justified.

| Same-session pair | Baseline median | Candidate median | Median paired ratio |
| --- | ---: | ---: | ---: |
| Slow64 -> inverse-only fast64 |7.532032ms|2.718208ms|2.86838|
| Fast64 -> probability8 |4.559872ms|3.924480ms|1.15678|

The fast64 baseline drifts between sessions; do not combine these into a
universal speedup. The second pair compares different quadratures, records
changed RGB, and is **not** an optical-neutrality assertion. Large one-TEST-pixel
cost remains; neither pair proves practical whole-frame rendering.

The first timing build failed because a nested probe redefined the main macro;
the fixed namespace wrapper build and all failures are retained. The first
probability timing launch was attempted before its binary existed and exited127;
it is NOT a measured GPU packet. `probability-timing-02` is the completed packet.

## Safety / next work

Fresh post-normal-save baseline is `prelaunch.json`; ordinary launcher31038
saved all dimensions and exited0 before native work. Its41 ordinary-save files
are comparison-only, NEVER restored. No ordinary camera/time/terrain automation.
Final `restoration-before-relaunch.json` verifies41 saved files equal the fresh
post-save baseline, all original configuration bytes, normal pack/Mod hashes,
and disabled TEST entrypoints. Then ordinary Lab was actually reopened:
launcher16740 / hostJava3202154 / namespace26 / lockFD154. Root inspected runtime
13:01:38 and pause13:01:44, then final pause13:02:13. Images/log are retained in
`ordinary-runtime/`. No native GL after this handoff. The initial existing
OpenAL device failure remains observed/unfixed, not a shader failure.

Full shore/cloud/volume/radiance/weather/night/contact/physical-energy/motion
requirements remain active. Next: qualify actual reflected/source discontinuity
and general critical contexts, efficient practical full-frame source integration,
then reversible exact-UUID disposable-V2 Iris/near/deep/tilted/moving validation.
Do not automatically promote this TEST slice or relax any failed gate.
