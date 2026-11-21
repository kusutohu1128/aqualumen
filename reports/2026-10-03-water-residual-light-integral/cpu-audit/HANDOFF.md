# Independent saved native light audit

CPU-only auditor: `tools/water_residual_light_audit.py` SHA256
`537f0057149312c5974c1a89c873193f9f9c456c1c46fa523fdc5da5afb375f0`.
Synthetic audit-plumbing tests: `tools/test_water_residual_light_audit.py` SHA256
`bdd9f3592c09d937659ee6aa2b4163f6ba2baf04add89d00f73b670a53ad2d94`.

The auditor and tests are frozen after the first saved native STUB audit. The
auditor never executes GL, changes a shader, normalizes observed n/v, mutates
the frozen math implementation, drops invalid nodes, or renormalizes a rule.

## Commands and observed first result

`python3 -B -m unittest discover -s tools -p test_water_residual_light_audit.py -v`
passed all four tests. These are synthetic audit-plumbing tests, not shader or
model validation. Earlier missing-module construction RED was transcript-only;
no retained artifact is claimed for it.

`python3 -B tools/water_residual_light_audit.py reports/2026-10-03-water-residual-light-integral/native-stub-red-v1 reports/2026-10-03-water-residual-light-integral/cpu-audit/stub-v1-audit.json --expect RED`
exited 0 with `CONSISTENT saved RED` (this consistency exit is not model PASS).

STUB report SHA256:
`eb712c1279f9afbdbbb5ac44fec1c0d859a3c429efcd6c3d64d3bb1c3993228c`.

- All eight cases: 5,025/5,025 legacy-domain points and fixed-six input pins.
- All 229 telemetry/repetition/passive/negative-source comparisons passed.
- 408 raw, input, compiled-source and provenance digests recorded.
- Narrow candidate actual feature application: 0/5,025 (required 5,025).
- Other seven cases: 5,025/5,025 actual feature-applied-zero controls.
- Fresh saved n/C/v at all 5,025 points evaluated 643,200 light-domain nodes.
- 764 points failed the unchanged numerical gate; maximum C0 component error
  was 0.08406968556278326. All six pinned candidate continuous checks failed.
- Old GH3 alias negative control was independently observed.

## Scope and assumptions

The all-ROI comparison uses the frozen double light-domain 8-radial ×16-azimuth
finite rule from each newly observed raw n/C/v. It is an independent arithmetic
comparison, not convergence evidence at every ROI point. Separate unchanged
frozen continuous slope-reference targets are checked at the fixed six points;
their original convergence/tail/domain limits remain intact. The dependency
SHA256 is `f5b6db7013907ab4baf6e28df0542a2f2066ddaef1c8cdb6e8a28fc4e352de92`.

Source/config/observer seam erasure is byte-exact, controlled input radiance and
width expressions are exact, saved actual textures/map/VBO/matrices agree, and
all four attached stages/reflection values are checked. These are saved export
checks; the auditor does not independently query a live driver or prove that a
driver compiled exactly the exported bytes beyond the frozen harness contract.

Missing/malformed/nonfinite data, failed telemetry, invalid legacy domain,
unmatched fixed inputs, or an invalid light-domain node yields INCONCLUSIVE.
Qualified missing feature application or incorrect response yields RED.
Fallback is not relabeled as successful application. Existing STUB inputs and
old frozen CPU packets were read only. No native Sun, singular/global receiver
limits, energy/reciprocity, natural Iris, appearance/motion/FPS or shipping
acceptance is inferred. A GREEN native packet must be separately supplied and
audited into a NEW JSON file; this document does not claim such a result.
