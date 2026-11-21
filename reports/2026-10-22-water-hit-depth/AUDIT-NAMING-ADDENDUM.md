# Baseline audit predicate name

The first near baseline result in `baseline-near-audit.json` returned true under the overly broad field name `boundedDepthEyeConsistencyPassed`. Its actual predicate checked that baseline composite distance follows raster depth and disagrees with the optical point. It did not mean the old shader had optical-depth consistency.

The source is preserved as `audit-v1.py`. The current audit separates `baselineReproductionPassed` from candidate-only `boundedDepthEyeConsistencyPassed`. `declaredCheckPassed` is the mode-specific script exit predicate. The near baseline numeric data is recomputed unchanged into `baseline-near-audit-v2.json`; it supersedes the old predicate label, not the saved observation. No capture or failure is deleted.
