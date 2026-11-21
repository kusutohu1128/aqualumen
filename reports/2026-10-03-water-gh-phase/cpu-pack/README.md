# GH phase TEST pack — CPU construction handoff

Status: CPU-ready, not a visible-band fix or accepted shader release. No GL,
GPU, Iris, Minecraft, installation, API/model call or live-file action was
performed for this builder. Root owns all subsequent native and TEST runtime
work. This is Codex work, not a fresh Claude review.

The only parent is the sealed prepared physical ZIP from
`reports/2026-10-03-water-prepared-iris/cpu-pack/`, SHA256
`b0fe0a7badf12a97b707b013de581c71dcc3c6e6d3d52a56bd187d4976a6b452`.
It retains its inherited counters and MRT stores; "physical" means original
FINAL/physical display, not a claim that inherited instrumentation vanished.

## Public construction and recovery

Run from repository root, choosing a **new** output filename:

```sh
python3 -B tools/water_gh_phase_pack.py build \
  --parent reports/2026-10-03-water-prepared-iris/cpu-pack/Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip \
  --phase 45 --role diagnostic \
  --output /tmp/NEW-DIRECTORY/Aqualumen-ShoreProbe-world-gh-phase-45-diagnostic-v1.zip
python3 -B tools/water_gh_phase_pack.py recover \
  --candidate /tmp/NEW-DIRECTORY/Aqualumen-ShoreProbe-world-gh-phase-45-diagnostic-v1.zip \
  --output /tmp/NEW-DIRECTORY/recovered-parent.zip
python3 -B -m unittest tools.test_water_gh_phase_pack
```

Allowed phases are literal 0 and 45; roles are physical and diagnostic.
Only this new `cpu-pack` subtree or system scratch directories under `/tmp`
or `/var/tmp` can receive
outputs. Existing destinations, path aliases, shipping/other report paths,
unapproved parent hashes, archive traversal/symlink members, and candidate
tampering fail closed. Recovery validates the complete reconstructed member
dictionary and returns the exact original parent ZIP bytes, not a repack.

All changed originals and the parent ZIP are archived in each candidate.
The ZIP embeds expanded physical FS, observed FS when applicable, phase
helper, unchanged physical Sun helper, raw physical FS, and pinned expanded
VS/TCS/TES. Their names and hashes are in `WATER-GH-PHASE.json`.
Source snapshots under `source/` are evidence; use canonical `tools/` scripts
for commands because their repository-relative path handling is intentional.

## One causal phase variable

The 0 branch preserves the original node-expression bytes and arithmetic.
45 uses `L * (R * z)`: rotate standard nodes with
`(x-z,x+z)*0.7071067811865475244`, then apply the original Cholesky map.
Weights, node ordering, covariance formula, admission/fallback gates, input
parameters, guard, prepared context, phase 120 and tessellation factor 4 are
unchanged. A double-precision weighted mean/covariance CPU control is included;
it is not proof of actual shader transport or visible-band causality.

Sun48 source stays fixed. Executed node counts are **not** asserted invariant:
rotating the GH nodes may alter full/base admission and downstream cap calls.
Both full/base legacy calls use the same phase.

## Diagnostic same-invocation records

New layout `aqualumen-gh-visible-band-v1` is incompatible with the previous
covariance readback layout. Covariance remains unchanged in source but is not
exported here. Targets are `0,9,10,11,12,13,14,15`:

| Target | Actual stored value |
| --- | --- |
| C9 | All four `WNS_reasons` fields |
| C10 | `WNS_status.xy`, exact inherited countword, `WNS_status.w` |
| C11 | Original four-bit flags, copied grazing `resolved`, outer `receiverKind`, raw `reflectedHit.a` |
| C12 | Unchanged TES stage coordinates |
| C13 | Raw full `WR_status`, immediately after the full call |
| C14 | Raw base `WR_status`, immediately after the base call |
| C15 | Same final water `max(color,0)` RGB and actual authorized-call marker |

The post-old-helper getter resolves include order without an early reference
to `WR_status`. No tracing/classification or transport call is repeated.
Grazing copies the existing local value, not a recomputation. The call marker
is set inside the existing guard before the original call. All seven records
are zero on the existing nonwater path. Tagged observer erasure recovers the
phase physical expanded FS exactly; GH tag erasure recovers the original
residual helper exactly.

C13–15 declarations follow the actual parent's comment constants: RGBA32F,
clear true, literal zero clear color, and water blending off. CPU source
validation does not establish actual Iris allocation/flip/sampler freshness.

Physical FINAL is byte-exact original. Diagnostic FINAL is a real 4×2 atlas,
bottom-to-top tiles `physical C0,C9,C10,C11 / C12,C13,C14,C15`, each with the
same source UV. All seven record samplers actively display integer texelFetch
values, with signed RGB compression and an alpha strip. C15 uses original
exposure/tone/gamma without a second AA and shows its call marker in the bottom
strip. C0's tile retains original exposure/tone/gamma/AA and full-source pixel
neighbor offsets. This enables image/mask alignment but is not calibrated raw
color, a full-resolution appearance comparison, or physical timing evidence.
Actual C9–15 dimensions/format/bindings must still be observed at runtime.

## Actual CPU evidence and remaining gate

The TDD skill caused public tracer-first construction: missing builder RED →
zero physical GREEN, unimplemented 45 RED → rotation GREEN, diagnostic role
rejection RED → diagnostic/recovery GREEN. Logs 01–06 preserve those real
CPU failures/successes. They are packaging/source-contract RED/GREEN, **not**
shoreline behavioral RED/GREEN.

The final output guard also rejects protected repository paths independently
of `TMPDIR`. Its public error-priority tracer RED (log 08) used an invalid
parent so no protected file could be published even before the correction;
the original diagnostic-source snapshots are in `source-pre-output-guard/`.
This host-only safeguard changed no generated shader members or ZIP bytes.
Log 07 is the retained earlier four-test PASS checkpoint.

Final public suite: **5 tests PASS**, 1.561 s (log 09). It checks deterministic
ZIP bytes, all unchanged parent members, reversible source spans and exact
ZIP recovery, the diagnostic source/atlas/clear/blend/record contract, and
fail-closed public-command safeguards. Python AST syntax passed; scoped
`git diff --check` exited 0. No shader compile/link or runtime was executed.

Next: root independently validates native original/observer neutrality and
phase controls before any bounded TEST observation. No visible bands,
covariance diagnosis, physical improvement, frame-rate claim or promotion is
accepted by these CPU artifacts.
