# SAME-model conditional water sampling: progress, not adoption

2026-10-06, RTX3080Ti native GL4.6/NVIDIA580.173.02. Original Minecraft uses
GL3.2; native compilation/capture is not actual Iris attachment/visual acceptance.
Previous Evidence, phase0/45/atlas results and uncommitted production changes
were retained, not gratuitously replayed. No new candidate installed, no external
Claude/subagent invocation, no commit/push. Full docs/REALISM_GOAL.md stays active.

## Implemented and checked

- Same correlated Gaussian slopes/Smith closure; analytic support-conditioned
  proposal. Weight is the known Gaussian support probability, never a survivor
  count fit. Orthogonal proposal rotation preserves physical covariance, raw
  n/v and legacy radiance units. No distribution/power/eta² tuning.
- CPU16 independent shifts x4096 samples: rotated-proposal mean matches all four
  retained T/R coefficient gates. SE/replicates are saved; no certified confidence,
  temporal or low-sample convergence proof. Unrotated conditioning still misses
  three T gates; both estimates retained.
- Actual standalone GPU eight-MRT 4x64 fixture with typed actual sampler, exact
  uploaded/readback texture, queried attached shaders and byte-exact repeats.
  3904 selected-node scalar comparisons meet the predeclared node gates;
  16 zero/indefinite covariance/open-endpoint/cutoff controls reject exactly.
  x is generated on CPU, not an end-to-end GPU random sampler.
- First port failed8 transmitted-z gates (max5.22964e-5). CDF-only replacement
  reduces max to3.68166e-6, with unchanged optics/support/gates. Original rejected
  packet `gpu-capture-01` and failing tests remain; `gpu-capture-02` is GREEN
  only for these selected-node checks. No exact-CDF/distribution interval proof.
- Genuine tilted camera/real uploaded water geometry and opaque depth/C4 source
  fixture finally observes R hits. Dense:6867hits/8082misses, black->green R
  0->0.0729541704.64 proposal:48hits/16misses, R0.0732696131. Independent113 exact
  comparisons each verify geometry/depth/input/source controls. About0.43%
  response difference is not converged first-visible-object transport acceptance.
- Actual original four-stage MAIN,64 proposals per T/R branch,10 source controls
  (zero/diffuse/Sun/rain/absent/opaque/cave/Moon/wide-open/wide-opaque).920 exact
  raw comparisons and independent finite-estimator replay. Source-kind and
  unobserved/proxy counters, strict/invalid whole-original fallbacks retained.
  Sharp Sun/Moon48-node caps remain separate and use the same Smith kernel.
  Actual reflected misses still use the explicitly counted legacy scatter proxy;
  actual unseen air uses counted cave/access proxy, not known physical sky.

## Rejections and cost are part of the result

64 proposals do NOT satisfy dense coefficient convergence. Diffuse T estimate
0.0245060766132 versus dense0.0244136122902, absolute error9.24643e-5 versus gate
6.88272e-6. Wide-opaque estimate0.0299431891830 versus0.0298282473707, error
1.14942e-4 versus gate7.96565e-6. Two128/256 actual-context inverse-domain
refinements are saved, not rigorous interval or full independent-domain proof.
The original unchanged tight auditor rejects this candidate; preserved in
`source-64-main-01-tight-audit.err`. Separate finite-replay GREEN is not a relaxed
convergence gate. All source-unit, source uncertainty and energy limits remain.

Native draw-only one-TEST-pixel257x257 query,12 ABBA rounds,24 intervals per role:
disabled median0.051712ms (0.016384–0.158720), enabled9.577984ms
(3.881984–11.755520). Independent34 witness comparisons match the source packet.
The previous dense median72.354816ms is historical, not a same-session speedup
or a pixel/full-frame extrapolation. The64 implementation is still costly.
These are not Minecraft FPS and not a new1440p benchmark. Root causes to examine
next include24 bisection iterations with48-step tail-CF evaluations and proposal
variance at visible-source boundaries; convergence/cost must both improve.

Retained `make check` passes all11 program pairs and optical regressions on
NVIDIA. New tests: conditional4, rotated2, GPU4, source2. TDD produced real
coordinate RED->GREEN; diagnosis isolated only CDF. Fixture-order ValueError,
missing-module test bootstraps and audit-alpha bug are preparation/audit failures,
not shader optical regressions. All logs are retained. Alpha was erroneously
treated as rain radiance in audit-v1; regression test and final RGB-only audit
correct it without changing GPU artifacts.

## Safe ordinary handoff

Old ordinary client cleanly saved all dimensions/exited0 before native GL.
Fresh post-save baseline `...host-conditioned-Mfbnsa`:41 ordinary saved files,
no save restore. Pre-relaunch save/config/asset identity passed. Ordinary0.6/
physics0.2/configs and9 absent TEST entrypoints verified, no benchmark request.
Owned launcher31038 / hostJava3178676 / window62914567 / DISPLAY=:1; exact
ordinary session.lock FD154. Root viewed runtime12:34:13 and pause12:34:37.
No later native GL. Options/benchmark bytes match; Iris semantic values match.
Existing OpenAL failure remains unfixed; no audio-success claim.

`checkpoint.json`, `RESUME.md`, raw maps, final audits and `SHA256SUMS` retain the
bounded completion. No candidate Iris/natural/temporal/physical-energy or full
goal acceptance; mass-conserving fluid simulation has not been added here.

Algorithms: authored evaluation of [DLMF8.7.1](https://dlmf.nist.gov/8.7.E1),
[DLMF8.9.2](https://dlmf.nist.gov/8.9.E2),
[DLMF7.11.2](https://dlmf.nist.gov/7.11.E2). Fixed truncations and binary32
arithmetic are not exact math. Original Gaussian/Smith/Fresnel references and
limitations remain in the sealed prior reports. No copied shader-pack source.
