# Aqualumen 0.5.0 incident-Sun transport checkpoint

2026-10-02. Implemented and runtime verified, but **the full realistic water and
sunlight goal remains open**. Work and independent audits are Codex work; no new
Claude invocation is claimed. The previous releases and evidence are retained.

## Artifact and causal correction

Built/installed/selected/runtime-active `Aqualumen-0.5.0.zip` SHA-256:
`88ff19eed363ff3d25287b3873ed7c0ac7b2ca654074e0365d510fedd07c859d`.
Physics0.2.0 is unchanged. A rebuild reproduces the same ZIP bytes.

The old receiver lighting accounted for an outgoing water path but omitted the
incident water path of its raw direct-Sun base. Only the paired direct-Sun
component is now replaced by its mean-horizontal-interface Snell path,
Fresnel-admitted fraction and RGB Beer transmittance; its focusing follows that
same energy correction. Ambient/Moon/block light is not incident-Sun attenuated.
The existing outgoing eye attenuation remains separate. Unknown above-water
proxy receivers are deliberately not treated as confirmed wet bottom surfaces.

Three successive production-main failing-then-passing controls are preserved:

- Underwater composite with a fixed1m eye leg and incident depth1.5→3.5m:
  old RGB direct-response ratios `(1,1,1)` become
  `(0.527292,0.843665,0.932394)`, agreeing with independent Beer references.
- The next absolute normal-entry test fails on Beer-only transport; adding
  Fresnel reflectance0.0203732 gives measured RGB response
  `(0.088035,0.118813,0.0897553)`, matching admitted-power references.
- Actual above-water vertex/fragment main with bed depth1.5→3.5m and fixed
  eye/interface: outgoing-only ratios `(0.527296,0.843645,0.932368)` become
  two-leg ratios `(0.278069,0.711784,0.869316)`, independently expected
  `(0.278037,0.711770,0.869358)`. Positive paired responses prevent a fake pass
  by deleting direct Sun. Lit/unlit C4/C8 are varied coherently.

See [native logs](native/) and the detailed [slice record](WORK-IN-PROGRESS.md).
The [frozen full check](native/frozen-final-check.log) passes11 graphics pairs,
3 compute programs and retained atmosphere/sky/opaque-MRT/Fresnel/TIR/cave/
eye-coordinate/continuous-bed/foreground-bank/wave regressions on RTX3080Ti,
NVIDIA580.173.02, native GL4.6. These are production shader correctness probes,
not Minecraft FPS. The30 benchmark/PNG/report/fixture Python tests also pass.
Earlier fixed-total-RGB/C8-only controls establish channel attribution, not a
separate positive-focusing proof after replacement of the direct-Sun base.

## Actual Minecraft views

The exact UUID-guarded disposable V2 [run](real-view/run.json) completed at
`2026-10-01T20:32:25.565043684Z`:16 scenes,1600x900,12/6 chunks, default BALANCED,
VSync off,5s warmup/5s sample, all focused and active without shader fallback.
Actual Minecraft reports GL3.2; the native GL4.6 context is not substituted.

The [independent data audit](INDEPENDENT-AUDIT.md) validates16 strict PNGs,
24,701 positive raw render-tail intervals, metadata/eye/physics exports and
recomputed statistics. The unmodified `tools/report.py::load_run` rejects1600x900
as designed; this is a separately audited quality/compatibility workload, not
a newly accepted1440p performance run. Frame-limit260 is the requested setting,
not proof of an enforced260-FPS display cap; some recorded interval-derived
rates exceed it. No minimum-FPS or arbitrary-world timing guarantee is made.

The [independent visual audit](../../docs/reviews/codex-v0.5-visual-audit.md)
retains observed underwater-sky/cave/glass/Nether/End compatibility but confirms
strong cyan/mint shallows and serrated dark/clear bands remain. The same-pose
1600x900 coast reference differs in wave phase, entities and contacts, so it is
not a fixed-phase causal pixel comparison. No0.5 temporal-naturalness acceptance
or broad visible improvement is inferred from these stills.

## Normal runtime and data safety

After completed cleanup/save evidence, instrumented TEST shutdown stalled again.
Only its exact identified Java and own launcher were terminated; the shutdown
defect remains open. The [persisted AIR audit](fixture-after-test-stop.json)
checks390 cells in six historical disposable plots and the absent ownership
journal. These checks and completion flags are not whole-world/entity integrity
proofs. No ordinary-world test automation, teleport/time command or terrain edit
was used.

Benchmark JAR/marker are recoverably inactive as `.0.5-release-disabled` copies.
Ordinary options are byte-identical to the pre-test snapshot, SHA
`02516270fea53cc286dceb1d5eca457f2ecc2e0ab6d2e1b15b01c4032307e5f0`,1600x900,
cap120, pause-on-lost-focus true. The [normal handoff](ordinary-handoff.json) and
native [current](user-scene/current.png)/[paused](user-scene/paused.png) views
confirm a fresh ordinary-account world launch, active0.5 and physics0.2.0, and a
paused game. Its latest pre-test save was preserved until normal relaunch; normal
saves naturally resume afterwards. The old0.3.3 handoff position was not forced
onto the user's newer save.

## Limits and next work

This uses one local horizontal plane, not a water-membership map. Arbitrary
receiver normals retain their air-lit cosine/shadow; bent-ray shadows, separate
pools/dry pockets, incident diffuse transport and source-depth in-scattering are
not solved. Stronger incident extinction can make the red/blue ratio lower, so
the patch is not claimed to desaturate the actual cyan shore defect.

Next, isolate optical-normal/geometry mismatch, view-depth wave attenuation,
SSR source switching and discrete refraction-bank boundaries one variable at
a time, then revisit real-view and temporal evidence. Natural rowing/wakes,
spatial cloud shadows, cloud shape and solar-disk/direct-beam energy coherence
remain required by the [full goal](../../docs/REALISM_GOAL.md).
