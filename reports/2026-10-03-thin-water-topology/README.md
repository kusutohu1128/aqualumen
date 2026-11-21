# 0.8.6 thin-bottom checkpoint — full realism goal incomplete

Codex, 2026-10-03. This is a tested local topology correction, not acceptance
of realistic water, shores, clouds or motion. Diagnose/TDD kept one causal
shader change separate from appearance tuning. No new Claude/API call occurred.

## Reproduced defect and bounded correction

The [0.8.5 checkpoint](../2026-10-02-underwater-reasons/README.md) fixed opposite
windings of the same confirmed water top. Its four-metre bottom negative did
not cover thin water: the shared column-height tolerance is 0.12m, while the
pinned Sodium bottom at block-local Y .001 is only .110111m below level-1
water's 1/9 surface. It can pass the same-height query.

The independent [source review](source-review.md) identifies a possible vanilla
counterexample: slime has a full collision/redstone-conductor floor predicate
for the column bridge but no occlusion, so a fluid bottom need not be suppressed.
This is primary installed-bytecode reasoning, not a live slime-world screenshot.

Native original VS/FS execution on the RTX3080Ti reproduces the alias in the
[v3 RED](native-red-v3/THIN-SUMMARY.txt): bottom geometry changes by
0.0015725158154964m, vertex unknown weight becomes 0, raw/final known and upper
surface become 1. The declared binary32 gamma512 geometry allowance is
0.00012970366527299m; whole-C0 STORE observation/repeat differences are exactly 0.

The ONLY shipping change versus 0.8.5 is negative-horizontal VS admission:
`known && fract(undisplacedAbsolutePosition.y) > .01`. Positive tops, the .12
shared tolerance, FS, waves, Fresnel/TIR and transport remain byte-identical.
Rejected bottoms retain the original VS unknown weight 1, so the existing
contributing-vertex FS gate rejects promotion. [The isolated diff](negative-vs-only.diff)
includes the source comments and this single condition.

The same v3 binary and fixture give [GREEN](native-green-v3/THIN-SUMMARY.txt):
zero original-VS geometry change, weight 1, raw known 1, final known 0, upper
surface 0 and zero optical-normal error. The raw column result is deliberately
NOT forced false. FS position and normal preservation are rechecked in v5.

## Neighboring GPU controls and limits

[v5 top controls](native-controls-v5/TOP-CONTROL-SUMMARY.txt) pass 25 cases:
five supplied top heights at block Y -64/-1/0/64/319, with both windings,
typed RGBA32F input readback, raw known 1, both vertex weights 0 and both FS
known/upper flags 1. Geometry and optical-normal differences are exactly 0;
whole-C0 STORE differences are 0 and positive waves remain nonzero.

The conservative corner `1/36-.001` is a stress lower bound, not an attainable
isolated corner. The pinned isolated corner is `1/27-.001`; dry neighbors may
make its column unknown. Uploaded all-valid maps are admission/envelope tests,
not proof of natural corner cache availability. The top cases use an explicit
fixture-only .001 near plane, NOT a changed Minecraft camera setting.

[v5 air-bottom controls](native-controls-v5/AIR-BOTTOM-SUMMARY.txt) pass five
block heights, viewed from below the one-block floor at camera Y block-1.05,
air flag 0, with actual GL_BACK culling ON. The negative winding renders at the
fixed centre; original geometry/weight remain unchanged, raw known stays 1,
final known/upper stay 0 and normal error is at most 5.9604644775391e-08.
No slime geometry, live occlusion implementation or world meshing is emulated.
The initial v3 underside-from-inside test has culling OFF and is only an input
contract regression, not an ordinary visible-bottom viewpoint.

Retained deep same-top, four-metre bottom and invalid-column backtop controls
also pass. The source review's temporary CPU sweep implementation was not saved;
its numbers are explicitly NOT reproducible acceptance artifacts. Neither those
numbers nor the native five heights prove arbitrary mod heights, every head-bob
transform, encoded live meshes, mixed triangles or unknown-top symmetry.

The [full native suite](full-native-green.log) compiles/links all 11 pairs and
3 compute shaders and passes retained optics, atmosphere/cloud/MRT, ripple and
solar checks. Separate near-reflection, water-radiance, bathymetry-gradient,
first-visible-bed/waves and solar-cloud-observer checks pass; their logs and
raw artifacts are retained here. ALL GPU work finished while Minecraft was
normally stopped. The opt-in backface CLI remains separate from default check.

## Actual Iris integration and visual result

The [shipping run](shipping-smoke/run.json) captures coast, river and three
approved underwater-up poses without terrain placement. Only disposable V2
UUID b22dbccb-2970-41e6-847f-f183b1ec923d / seed308060 received camera/time requests.
It uses the matched normal account, physics0.3, benchmark0.3.9, candidate0.8.6,
1600x900, chunks12/6, cap120, vsync OFF and 5s warmup + 5s sample per scene.
All five actual captures are focused, active and nonfallback; actual underwater
camera/eye alignment, WATER submersion and requested depths are checked.

[Independent CPU audit](runtime-audit.json), rerun by root byte-identically,
checks full PNG CRC/decompression/dimensions, integer-ns CSV and recomputed
metrics, installed versions, poses, recorded allocation/restored binding and
exact ZIP hashes. The five scenes contain 2713 intervals / 24,980,734,511ns;
mean FPS is 92.2033–118.5374, worst interval 14.036704ms and 16.667ms exceedances
are 0. This is a short capped 900p observation, NOT 1440p or a 60FPS floor.
CSV milliseconds follow Recorder's binary64 `ns * 1e-6`, not exact decimal
division. Eight CPU audit self-tests pass; retained pack/readback CPU tests pass.
Allocation metadata is not per-fragment consumption or same-frame fetch proof.

Root visually inspected all five PNGs. [Near](shipping-smoke/underwater-up-near.png),
[deep](shipping-smoke/underwater-up-deep.png) and [tilted](shipping-smoke/underwater-up-tilt.png)
views still have severely undulating/wrinkled sky-window rims and a uniformly
dark exterior; deep water also shows isolated small square particles.
[Coast](shipping-smoke/coast-day.png) and [river](shipping-smoke/river-day.png)
remain strongly cyan/mint with pointed jagged bands, stretched reflections and
procedural/repetitive clouds. The former square sky seam is not observed, but
natural appearance is NOT accepted. These are different frames/phases from
0.8.5, not a controlled pixel A/B. No new motion/rowing acceptance occurred.

## Artifact and safe handoff

Candidate [Aqualumen-0.8.6.zip](Aqualumen-0.8.6.zip) SHA256:
`16a7da88b7a5ba11d6aadfd56c717875fc61153b81cc859b4503da620c56c9d0`.
Dist and installed Lab ZIP are identical; only VS differs from 0.8.5, all other
46 entries agree. Earlier archives and the frozen657-entry 0.8.5 evidence packet
are preserved; its manifest still hashes to
`28467b5f408c4ad4bd63ebbdf11f6e5ac6a6fd6befe91fb9f9fd42f9ad29e1c3`.

Ordinary game3560726 saved all dimensions at04:41:52 and exited normally0 at
04:42:55 before GPU work. A NEW post-save backup was taken; no save was restored.
The candidate game3583734 saved all dimensions at05:00:12 and exited normally0
at05:01:22; both owned PIDs were absent. Persisted
[390-cell AIR/no-journal audit](fixture-air-after.json) passes. Ordinary saved
files match this turn's fresh post-save backup BEFORE normal relaunch.

Original options and benchmark properties remain byte-identical. Iris config
was restored byte-identically before relaunch; its timestamp comment can
naturally regenerate on launch. Benchmark marker/JAR and physics0.3 are
recoverably disabled, all previous disabled files remain, observers are disabled.
Ordinary0.6/physics0.2 is reopened under the normal account3590475 at05:02 and
[actually paused](ordinary-restored-paused.png) at05:03:29. Candidate0.8.6 is
installed but NOT selected for ordinary play. Autosaves after relaunch may
naturally change the ordinary world; no ongoing saved-tree identity is claimed.
No ordinary-world camera/time/terrain automation, signal kill, commit or push.

For a native rerun, first stop Minecraft normally; use a NEW artifact directory:

```bash
make build/glcheck
build/glcheck shaders --underwater-backface-only NEW_ARTIFACT_DIRECTORY
```

CPU capture audit is independent of that native run:

```bash
python3 tools/test_thin_runtime_audit.py --self-test
python3 tools/test_thin_runtime_audit.py reports/2026-10-03-thin-water-topology/shipping-smoke
```

Next work must still address unknown/mixed-top symmetry, reflected-light
provenance offscreen, a possible coarse-geometry/optical-facet mismatch and
natural shore/cloud/motion behavior. Do not substitute forced known flags,
air-sky fill, a different IOR or brightness/color tuning for a causal physical
fix. Dedicated Mod work remains available within the full original goal.
