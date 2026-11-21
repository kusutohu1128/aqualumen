# Prepared independent Iris replay

`audit.py PACKET` is CPU-only and prints JSON; it does not write results, control
Minecraft or call GL. Actual captures have not been audited at preparation time.
Missing or incomplete files fail closed rather than generating expected data.

Expected layout: four `iris-{reject|zero}-{reasons|inputs}` directories, each with
`final-raw.json`, `guard-raw.json`, `stage-raw.json`, root `reason-audit.json` or
`input-audit.json`, and `run/` containing the complete near-view PNG/CSV/JSONs.
The four frozen ZIPs live in `cpu-pack/`; retained read-only Lab aliases must
match them byte-for-byte. No accounts or ordinary-world files are inspected.

The checker pins the current NEW public auditor and independently checks exact
source recovery, all16 fixed raw observations, packed counts, Fraction support
and Decimal80/120 first-target references, PNG integrity, integer-nanosecond
metrics, held camera, separate prepared int1 and attached stage hashes.
The predeclared warmed-view controls remain 10s warmup/5s sample, 1600x900,
120 cap, VSync off, 12 render/6 simulation chunks. These are not 1440p or
uncapped-throughput results. The original four-point application minimum stays
unchanged. A valid negative
application result is not converted into adoption by an evidence-replay PASS.

Cross-capture mean/view/covariance/flags and available target/index bits are
reported explicitly. No first target means only `NO_OBSERVED_FAIL`. Disappearance
does not prove zero support. Neither selected counters nor first-target replay
prove every node, continuum-zero, Fresnel/TIR zero, exact GPU arithmetic, pixel
AA, natural appearance, motion, 1440p performance, an FPS floor or shipping.

## Completed saved-data replay

`actual-audit.json` is the independent replay of the four completed captures,
not synthetic test data. SHA256:
`e8120384815a7aafb64b3cb554fa590ed035d39274062db0f89a389a357fc8c1`.
The unchanged `audit.py` SHA256 is
`911265553e2f44cf6ea475cdb3a69343fb9f7d5ae75be18ba012aa2f7133315f`.
All four PNGs, 252 positive integer-nanosecond intervals, exact pack/source
recoveries, separate prepared guards, four-stage observations and selected
readbacks passed their saved-data contracts. Twelve temporary-copy corruption
tests passed; the incomplete packet also failed closed. These checks changed no
original capture or installed artifact.

The retained public CPU replay is
`python3 -B reports/2026-10-03-water-sun-support/cpu-independent-iris/test_saved_corruption.py`.
Its 12 tests are recorded in `cpu-corruption-tests.log` and are separate from
root's aggregate 41-test run. They copy actual saved records into disposable CPU
directories before corruption; the incomplete-packet observation is not an
additional counted test. Test source SHA256:
`e73579d2e26f2247c03f4c8c42bfc383f4b4a417eeaf0d4cdd07edfd728b1c2e`.
Log SHA256: `8ffc43d28085c1c119df8789c83e53c085b9509a7619b0c7105fc9f4dac2d1a9`.

At all16 input points, cross-policy mean/view/covariance/flag bits match; actual
rewritten geometry-stage hashes also match across all four captures. Reject
remains `NEGATIVE_INSUFFICIENT_APPLICATION` at 2/16. Zero passes the unchanged
selected-application minimum at 12/16, with 16 complete48-call ledgers:
502 absent, 266 supported, 0 unknown, 768 total calls. The ten reject firstReason2
targets independently classify absent under the prescribed incident-facing
branch; their later code0 means no observed failure, not a zero-integral oracle.
The four remaining firstReason3 targets retain the same target/index bits and a
supported branch. The Decimal replay's hypothetical binary32 numerical failures
at two of those points are not observations of the current GPU's failure cause.

| Capture | Intervals | Mean FPS | Worst interval ms |
| --- | ---: | ---: | ---: |
| reject-reasons | 64 | 12.96690449 | 78.378021 |
| reject-inputs | 64 | 12.97126528 | 78.790196 |
| zero-reasons | 62 | 12.55899385 | 81.117832 |
| zero-inputs | 62 | 12.57256453 | 80.526858 |

Every measured interval exceeded the 16.667ms reference. This severe performance
limit is retained, not excused by the 120 cap. These are short warmed900p views,
not a performance-causality experiment, FPS-floor guarantee or release approval.
The separate native six-case packet did not exercise a positive absence branch
(`zero_branch=false`); the actual Iris count ledgers above are the observed branch
evidence. Natural appearance, native pixel-AA, energy, reciprocity, motion,
shipping and full-goal acceptance remain false.
