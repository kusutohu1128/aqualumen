# Native Sun integration checkpoint

2026-10-03: **progress, not overall completion or shipping acceptance**.

A separate TEST cap helper now integrates the small native solar disk in
light-direction space instead of relying only on the legacy slope nodes to
sample it. Native source radius, transmission cache, weather factor, geometry,
scatter and legacy Fresnel/transport units are retained. The cap is48 positive
nodes, with saved-full legacy fallback when the entire replacement cannot be
qualified. Existing production shaders and the user's selected0.6 pack remain
unchanged.

## Verified outcome

Root executed the same frozen native exporter binary on the actual original
four water stages, first with the STUB and then with the CAP. Both16-case
exports completed. A separately implemented CPU audit qualifies actual queried
source/input/storage, raw binary32 vectors, repeated draws and full legacy
domain before testing numerical response.

| Gate | STUB | CAP |
| --- | --- | --- |
| Actual legacy/request domain, each of16 cases | 5025/5025 | 5025/5025 |
| Numerical + actual application, positive-enabled observations | 0/40200, RED | 40200/40200, PASS |
| Telemetry/control checks | 444/444 | 444/444 |
| Selected GPU response versus refined12x48 reference | 0/48 | 48/48 |
| Selected finite4x12 versus refined12x48 reference | 96/96 | 96/96 |
| Selected8x24 versus12x48 convergence | 96/96 | 96/96 |

The40200 count is4 positive-enabled fixtures x5025 fixed ROI pixels x2
pure/observer renderings, not40200 independent conditions. The CAP applies at
all20100 eligible pixels across those4 fixtures. Other12 cases remain
unapplied; actual zero-cache enabled1 means requested1/applied0, full legacy.

Numerical component gate was fixed before GL: abs2e-6 +
rel2e-4*abs(reference). Maximum CAP error/gate ratio is0.007234742; maximum
whole-ROI finite-reference absolute C0 error is0.005613146. Selected GPU versus
refined reference maximum error is0.001944007. Selected finite4x12 versus12x48
maximum difference is2.774e-11;8x24 versus12x48 is2.274e-12. Whole ROI is a
finite-rule check; only the predeclared six selected pixels receive refinement.
No whole-ROI or arbitrary-covariance convergence claim is made.

Solar response is `(C0_positive-C0_zero)-R_legacy*(scatter_positive-scatter_zero)`
using actual separate same-enabled zero-cache draws and measured coefficients.
Positive cache also affects reflected water scatter; that coupling was not
disabled or silently counted as solar transmission.

An independent crosspack raw comparison also passed: all12 inactive cases
retain zero C0 difference,96 observer RGBA maps are byte-identical,176 actual
input/VBO/bathymetry uploads are identical,64 depth maps match exactly, and all
common n/v/scatter/covariance/WR/status comparisons have difference0. Only active
C0 and feature-applied alpha change. This is bounded control neutrality, not
arbitrary-world non-regression.

Root reran42 public CPU tests, all PASS. Root `make check` passed11 production
program pairs and the retained water/caustic/solar numerical regressions on the
RTX3080Ti. Those are not new Sun appearance or Minecraft FPS benchmarks.

## Evidence

- [Predeclared experiment](EXPERIMENT.md), [static plan](STATIC-PLAN.md) and
  [actual STUB RED](STUB-RED.md).
- [CAP audit handoff](cpu-audit/CAP-HANDOFF.json), with exact final report/source
  hashes; `cpu-audit/cap-v1-audit.json` is the independent saved-data PASS.
- [Crosspack controls](crosspack-independent-audit.json): independent exact
  inactive/source/input/depth comparison, separate from the numeric integral.
- `native-stub-v1/` and `native-cap-v1/`: actual raw MRT/depth exports, exact
  queried stage sources, typed uniforms/matrices, VBO, input textures and repeats.
- `cpu-probe/`: frozen executable/source/build receipt and dependency snapshots.
- `cpu-pack-stub/` and `cpu-pack-cap/`: separate immutable TEST ZIPs and manifests.
- `source-stub/` and `source-cap/`: copied source/test provenance, not shipping
  installation directories. `root-final-cpu-tests.log` and
  `root-native-baseline.log` retain root-run checks.
- [Normal game lifecycle](ORDINARY-LIFECYCLE.md) and inspected fresh paused
  screenshot `ordinary-restored-paused.png`.

## Explicitly unverified

Native `sunDisk` has derivative pixel coverage. This checkpoint proves a bounded
**central physical sharp-disk numerical response**, not equivalence with that
filtered Sun and not a demonstrated bug in its continuous filtered integral.
No native pixel-AA acceptance, near-singular covariance/rim/critical/occlusion
qualification, global energy/reciprocity proof, new Iris runtime/visual/motion
acceptance, FPS measurement, or adoption is claimed. Native probe inputs use
an open receiver and diagnostic NEAREST/base-level storage. Actual Sun axis and
skyWeight are derived from queried native inputs/formulas, not direct per-node
GPU observations.

The new TEST ZIP has no UUID world guard and must not be installed as a normal
play pack. Its48 nodes and two unconditional legacy calls can require up to132
traces, so performance and actual filtered receiver behavior require separate
testing. The normal0.6/physics0.2 game has been relaunched and left paused.

See [next checkpoint](NEXT.md). The broad realism goal remains active.
