# Operation-tree follow-up (CPU only)

V1 exports, logs, source/test snapshots and HANDOFF.json are unchanged. V2 adds only a separately declared candidate-tree observation under `binary32.candidate_tree`; removing that field from either new correlated export exactly recovers the prior JSON value.

The expanded model computes `round(round(c*x)-round(s*y))` and `round(round(s*x)+round(c*y))`. The actual candidate phase45 expression instead computes `round(round(x-y)*c)` and `round(round(x+y)*c)`, with literal `0.7071067811865475244`. This literal and the V1 declared `0.7071067811865476` both round to bits `3f3504f3`. The test compares independently evaluated trees, not a shared precomputed result.

All nine pairs from `{ -float32(sqrt3), +0, +float32(sqrt3) }^2` have identical white-output bits; all nine correlated Cholesky outputs also match. Phase0 identity and expanded expressions match all nine pairs too. This finite-grid equivalence follows because sums/differences are only zero, one abscissa, or an exact doubling; multiplication-rounding commutes with that exact power-of-two scale in this normal finite range. It is **not** general floating-point distributivity or arbitrary-input equivalence.

Evidence: public ninth test RED at missing candidate-tree observation, then GREEN with all nine tests passing (`19-...`, `20-...`). `21-v2-preservation-verification.log` verifies all five old output hashes and unchanged pre-existing output fields. Fresh source/tests and the two new exports are pinned in HANDOFF-v2.json.

Nearest/ties-even after each primitive, no FMA, canonical positive zero, exact rational moment sums: GPU optimizer/FMA/accumulation/signed-zero equivalence remains unaccepted. No GL, shipping or runtime writes occurred. All V1 physical/convergence/appearance/shipping limitations remain.
