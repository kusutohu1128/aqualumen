# 0.8.6 TEST-only underwater facet checkpoint

The normal-only diagnostic completed in actual Iris on the RTX3080Ti. It is
not a shipping fix, natural-water acceptance or completion of the realism goal.
Production shaders and `dist/Aqualumen-0.8.6.zip` were not changed in this slice.

## Outcome

Root reviewed all six near/deep/tilt images, plus the retained control-near repeat.
Facet reduces the fine deep-view rim folds/holes, but introduces large triangle
seams from the coarse displaced mesh. Near becomes more symmetric; tilted/deep
views show the coarse facets clearly. The dark exterior remains. This supports
the normal/geometry representation mismatch as a major contributor to the fine
folds, not as a complete explanation of the user's underwater appearance.

Do not adopt the facet assignment. The next separately qualified representation
and geometry-stage slices are described in
[the source review](codex-underwater-bandwidth-tessellation-next.md).

## Measured, nonvacuous diagnostic

Both packs share the same atlas/MRT and common analytic phase120. The sole
paired shader difference is one existing known-column optical-normal assignment.
All 47 original entries/hash metadata match shipping0.8.6; each diagnostic ZIP
contains 96 entries. VS, IOR, known/bottom guards, trace/transport and FINAL match.
The fixed phase does not freeze contact solver, bathymetry, entities or weather.

[Root's audit](runtime-audit.json) is byte-identical to the independent public-route
audit. Every row below qualifies all 16 fixed selected points (4 interior, 12 edge),
with all 16 flag sets matching and all 16 optical-normal responses above .001.

| View | Max normal component delta | F>=.9999 control/facet | Threshold toggles | SSR miss control/facet |
| --- | ---: | ---: | ---: | ---: |
| Near | .1909243911 | 0 / 0 | 0 | 16 / 16 |
| Deep | .2200811617 | 5 / 3 | 4 | 16 / 16 |
| Tilt | .1558618145 | 6 / 8 | 2 | 16 / 16 |

The Fresnel threshold is the shader's reflection-only classification, not an
independent true-TIR measurement. Near selected points do not observe that
reflection-only region. All 96 role-points miss SSR; this does not prove the
whole image misses, or restore an offscreen receiver. C9 dark purple is the
encoded downward known normal, not the bright-magenta unknown marker. C11
bright magenta is the miss flag. No selected near C9 point is unknown.

Actual FINAL scalar C9/C10/C11 samplers are active, distinct-bound RGBA32F,
1600x900 and finite. Eleven GL states are restored. The available typed inverse
view matrices match exactly within each raw pair; see
[the separate comparison](raw-inverse-view-equality.json). Full geometry
attribution remains false because required projection/camera uniforms are
inactive. Neither matrix equality nor the audit establishes PNG/raw same frame.
Raw observations follow completed captures, with exact matching camera positions;
the raw observer has no separate player rotation, submersion or Sun-time query.

The near raw-first observation belongs to `control-near-initial`, not the later
`control-near` repeat. The two PNGs are byte-identical; their run/timing records
remain separate. Seven five-second warmed, focused 900p/cap120 views were checked
by integer-ns CSV replay and full PNG CRC/zlib/CPU image decode. Timing does not
accept a 60FPS floor, 1440p, motion or diagnostic-free shipping performance.

## Verification and retained failures

Builder: 15 CPU packaging tests pass. Auditor: 7 synthetic CPU boundary tests
pass. Root reran both; logs and tool snapshots are retained. Tests distinguish
synthetic boundaries from actual captures. Native compile/link passes for both
packs, explicitly without draw/readback/neutrality or visual acceptance.

The first request was queued before an integrated server existed and aborted.
Its status is retained; the same live JVM then completed the test. This was not
a shader failure. The auditor's first actual route found missing Pillow; its
software-dependency failure is retained. The completed route uses existing
ffmpeg with hardware acceleration disabled after CRC/zlib validation, without
installing a package. Neither failure was erased or promoted into shader RED.

Pack hashes:

- Control: `8b054a95693a997cde7c3b8f8d4097f593309584067ac1d3c9c77887dba4239d`
- Facet: `8cac459d1ae717bc83719c6a0c76e950b5b05926e4124d5134a004115f97dd9b`
- Root audit: `e6251110f5ba2db34ab26f4e77bb82bcb0310b32ad9ccd62c07ec929731b6d2e`
- Auditor: `32de4de6e2e90aeb3dea3b31f64ffdde52ea87f8fe06ef4cca03a571c2c0e36f`

Recheck from the repository root, CPU only:

```sh
python3 -B tools/test_underwater_probe_pack.py
python3 -B tools/test_underwater_facet_audit.py --self-test
python3 -B tools/test_underwater_facet_audit.py --report-dir reports/2026-10-03-underwater-facet
```

Snapshots are frozen identity evidence, not scripts to run from this report
directory; the audit deliberately references the pinned repository shipping ZIP.

## Lifecycle and handoff

Ordinary `新規ワールド` was saved/quit before native GPU work. A fresh post-save
private backup was used for comparison only, never restored. Before ordinary
relaunch its complete tree remained byte-identical. No ordinary camera/time/
terrain automation was performed. Only exact approved V2 UUID/seed/noise scope
received test camera/time controls, with no terrain placement.

Control server saved all dimensions 05:27:23 JST; facet saved 05:36:05 JST. Both
owned launch sessions exited0 through Save-and-Quit/title-Quit, without signals.
After each test, persisted fixture audit found exactly 390 AIR cells and no
pending journal. Configs/options were restored byte-for-byte before normal
relaunch, and the diagnostic JARs/markers were recoverably disabled. Ordinary
0.6.0 + physics0.2.0, no benchmark, was reopened and paused 05:41:29 JST. Iris may
regenerate its date comment on load. Diagnostic ZIPs remain installed but not
selected. No native GPU work occurred while a Minecraft JVM was live.

Goal remains active. No commit/push or production normal replacement was made.
