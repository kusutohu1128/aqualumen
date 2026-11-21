# Saved GREEN independent CPU audit

The unchanged frozen auditor used for saved STUB RED was run against completed
`native-integral-v1`, with no GL or app action by this auditor:

`python3 -B tools/water_residual_light_audit.py reports/2026-10-03-water-residual-light-integral/native-integral-v1 reports/2026-10-03-water-residual-light-integral/cpu-audit/integral-v1-audit.json --expect PASS`

Exit 0: `CONSISTENT saved PASS`. Report SHA256:
`5274e5cb03cff49fea67ea317ee6d930e5f1bc50b0989bc74163a87d7cae31c5`.

- All eight cases: legacy domain 5,025/5,025 and unchanged fixed-six input pins.
- Narrow candidate: actual feature-applied 1 at 5,025/5,025 points.
- Other seven cases: actual feature-applied 0 at 5,025/5,025 points each.
- All 229 telemetry/repetition/passive/source-control comparisons passed.
- 408 raw/source/input/provenance SHA256 entries recorded.
- Fresh saved raw n/C/v inputs produced 643,200 double kernel evaluations;
  all 5,025 finite 8×16 comparisons passed. No CPU node-domain failures.
- Maximum C0 component absolute error: 8.241482283080637e-9.
- Maximum error / unchanged declared gate ratio: 0.0018327811368811606.
- All 12 candidate fixed-six pure/observer comparisons with the unchanged,
  independently converged continuous slope targets passed.
- The old GH3 alias negative control remained numerically mismatched.

No test, tolerance, source-width, radiance, observer, input or auditor changed
between STUB and GREEN audit. Frozen auditor SHA256 remains
`537f0057149312c5974c1a89c873193f9f9c456c1c46fa523fdc5da5afb375f0`;
the STUB report remains
`eb712c1279f9afbdbbb5ac44fec1c0d859a3c429efcd6c3d64d3bb1c3993228c`.

The full-ROI result is a comparison to the finite 8×16 light-domain CPU rule,
not convergence evidence for every point. The fixed six retain their separate
continuous-reference convergence/domain/tail limits. Source recovery checks
are exact saved-byte checks and the attached-stage evidence is saved driver
reflection, not a live query by the auditor. General varying fallback
derivative/implicit texture safety is not established by this derivative-free,
NEAREST/base-level fixture. No calibrated native Sun, global/singular receiver
limits, energy/reciprocity, natural Iris, visual/motion/FPS or shipping adoption
is inferred. All auditor sources, tests, STUB/GREEN reports and handoff notes
are now frozen; old native packets and CPU math tools remained read only.
