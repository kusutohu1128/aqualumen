# Aqualumen0.8.4 — bounded near-reflection checkpoint

The user wants realistic water and sunlight, not only shader compilation or
an easier passing native fixture. The full objective remains unfinished. Current ordinary
play remains Aqualumen0.6/physics0.2; candidate source before this slice is0.8.3.

The preceding [angular checkpoint](../2026-10-02-underwater-angular/README.md)
is frozen with254 files and manifest SHA256
`7e376e7c82d65f6766db993176b752f4fe4322650c5c9e358b183a6b81b1d275`.
It closes a flat native angular baseline, not natural underwater appearance.

## Ranked falsifiable candidates

1. A near visible underwater reflector is missed by the fixed previous-depth
   cutoff. Qualify a frozen original-main source response using actual bound
   input readback and an independent visibility/positive-response bound before
   calling this behavioral RED. A local repair is not an offscreen solution.
2. Analytic optical slopes versus coarse displaced raster facets cause excess
   rim distortion. Keep VS unchanged and ablate only the known-column optical
   normal to the actual raster facet in a TEST-only diagnostic pack.
3. The uniformly dark exterior is underwater reflection miss→scatter fallback
   because the reflected bed is outside the camera image. Observe the real
   reflectedHit path from the same water-main invocation, rather than changing
   IOR or substituting unrelated camera colors.

Actual near/deep/tilt captures still show a broad round window, wrinkled rim and
dark exterior, without the old rectangle/double sky map. The flat angular tests
do not justify removing the round window cosmetically. New same-invocation
MRT observations and a one-variable facet ablation are diagnostics, not fixes.

## Ordinary-world preservation

Fresh native F2 at17:55:27 confirms the existing ordinary game is paused.
Observed Save/Quit at17:55:58 saves all three dimensions; F2 at17:56:00 shows
the title menu. Observed Quit produces `Stopping!` at17:56:24 and launcher
session76054 terminal exit0. Both owned Java3030487/launcher3030390 are absent
before any new GL work; no termination signal is used. No ordinary-world
camera/time/terrain automation or restore is performed.

Fresh post-save ordinary-world/config backups are private. Options SHA256
`02516270fea53cc286dceb1d5eca457f2ecc2e0ab6d2e1b15b01c4032307e5f0`,
Iris SHA256 `466a5038b86276dd05c3c3035d6d5b44db85143110b1e774998c8cf341e36757`,
benchmark properties SHA256
`45a4c9b0269ec47b3a72fa73647e92702b6012be10f273a60d37f69c9ca148d1`.
The saved ordinary-world tree matches its new post-save backup byte-for-byte.
This equality is point-in-time evidence, not a claim of immutable future saves.

The approved V2 marker remains UUIDb22dbccb-2970-41e6-847f-f183b1ec923d,
seed308060, schema2, vanilla noise. Read-only saved Anvil audit at18:09:36
finds390 exact AIR reserved cells and no pending journal; region SHA256
`527a0227b6d18c912977b73077fd6d225a342ecd3a7a3800ea356e8525928442`.
This is a bounded fixture-cleanup audit, not whole-world/entity integrity.

## Qualified production-main RED and first GREEN

The frozen near129 pixel24,11/.3m scene now qualifies using actual bound typed
C4 RGBA32F/depth32F readback, original/store whole-image neutrality and repeat,
five independent physical/TIR/source footprint rays and one actual centre-ray
finite NEAREST-cell envelope. The preceding .55m positive response is .18808098.
The independent near red lower bound is .0687747164 and first receiver path
must lie in .2804767447–.3603223207m. Old production main returns zero gain/path−1:
[true RED](native-old-red/NEAR-SUMMARY.txt), terminal1 on real RTX3080Ti GL4.6.

The candidate checks the previous point against its OWN projected opaque depth
only when isEyeInWater=1. The old comparison used the current point's different
camera ray with a fixed .25m slack. The new predicate is a front-to-back bracket,
not blanket thickness expansion. All underwater faces use this policy;
above-water behavior, call signatures, crossing width, four refinements and
final edge/confidence policy are retained. First [GREEN](native-candidate-first/NEAR-SUMMARY.txt)
is .2039008737 gain/path .2999999225m under exactly the same input/oracle bounds,
terminal0. Existing full native11-pair/compute/optical/solar regressions also
pass terminal0 before runtime work. A subsequent [black-first negative](native-candidate-negative/BLACK-FIRST-SUMMARY.txt)
qualifies five physical footprint rays and215 nonvacuous camera-visible red
background footprints. All three original output channel deltas are exactly0:
the first black receiver does not leak the red background in this bounded test.
This is not generic silhouette/offscreen correctness or natural-image acceptance.

Candidate water FS SHA256
`17eb99c946d10aacc3d8a70b60fdbdaa55057c77ae40b2d2f5456c80a8d6fc08`.
This local visible-source repair cannot supply geometry outside the camera image.
The original large dark exterior and wave-rim appearance still require actual
diagnostic comparison. The circular Snell window is not cosmetically removed.

## Actual Iris diagnostic failure and correction

The v1 diagnostic ZIP compiles under native GLSL, but actual Iris1.8.8 at21:49:06
fails while parsing `colortex9ClearColor = vec4(0.0)`: its annotation parser
requires four scalar arguments and then throws ArrayIndexOutOfBounds. The
[actual runtime RED](actual-iris-atlas-parser-red.log) and v1 ZIPs are retained.
The diagnostic builder now writes `vec4(0.0,0.0,0.0,0.0)` for C9/C10/C11 only;
the added public-ZIP contract fails before and all10 CPU tests pass afterward.
The corrected v2 atlas also passes native compile/link, then actual Iris loads
it without shader fallback. Native compilation alone was not sufficient evidence.

The v2 packs use the current0.8.4 candidate as their explicitly archived basis,
not old0.8.3. Atlas SHA256 is
`210480da8bd06a3265ae09f165f1bf82042344bc3cab32e2e7abf9f639dcdf2b`.
Its [actual near/deep/tilt captures](actual-atlas-v2/run.json) record the exact
V2 UUID/seed, active shader/no fallback, focused1600x900 framebuffer, submerged
eyes at approximately0.50/3.25/0.50m, rotations−90/−90/−65 degrees and time6000.
No terrain placement occurs. C0 in the upper-left panel omits final AA taps;
these diagnostic captures are not native whole-image neutral shipping views.

Root sees the broad round sky window, wrinkled rim and dark exterior persist.
The right-hand panels are magenta in these observed views: the shader's atlas
legend represents an unconfirmed local-column flag and a reflectedHit miss.
PNG colours are not calibrated raw C9–C11 readbacks or an allocation/sampler
proof. No near/deep/tilt facet-ablation acceptance is claimed; changing a
known-column assignment may be inactive here. The next causal observation must
separate the actual optical normal/known-column input from offscreen reflection
misses, without changing IOR or adding arbitrary sky to the reflected bed.

The generic report tool refuses this1600x900 run because its contract requires
2560x1440; [that failed attempt](actual-atlas-v2-report.log) is preserved. No
1440p report or performance guarantee is inferred from these short diagnostic
captures. An existing OpenAL startup error remains outside this shader change.

Both failed v1 and corrected v2 clients use the matched ordinary account only
inside disposableV2. Observed Save/Quit saves all dimensions, title-menu F2
captures verify completion, and their owned launcher sessions exit0 without
signals. Saved390 reserved AIR cells/no pending journal are independently
[audited after the atlas](fixture-air-after-atlas.json). Ordinary saved files
still match the fresh post-save backup at22:02; no ordinary restore occurred.

The installable candidate [Aqualumen0.8.4](Aqualumen-0.8.4.zip) has SHA256
`9da92d1512cf7f4298ad99b6d6aa6e9a084c5eced851dda0089165904498ad2b`.
It is not adopted for ordinary play or evidence that the original natural
rim/dark-exterior complaint is fully resolved.

## Shipping-view smoke and handoff

Five [actual0.8.4 shipping captures](actual-candidate-v084/run.json) use the
original final display, no diagnostic MRT output: coast, river and underwater
near/deep/tilt. Exact pack SHA, approved V2 UUID/seed, focused1600x900, active
shader/no fallback and10s warmup/5s sample are recorded for all five. Root and
an independent reviewer inspect every PNG. Cyan/mint shallows, pointed jagged
bands, a rounded sky window and dark exterior persist. No original natural
complaint or full visual/temporal acceptance is claimed. Short warmed frame
observations are not1440p results or a universal60FPS floor. The independent
[PNG/identity/integer-ns audit](ACTUAL-CANDIDATE-AUDIT.json) checks2788 frames
over24.974 recorded seconds, with per-scene means99.663–118.560FPS, worst
12.725607ms and zero sampled intervals over16.667ms. The frame cap is120;
these short observations do not establish long-running or motion performance.

The candidate client saves all dimensions at22:07:54–55; actual F2 title menu
at22:08:14 and owned session87065 exit0 confirm clean shutdown without a signal.
The [saved AIR audit](fixture-air-after-candidate.json) again verifies390
reserved cells/no journal. All test/GPU work ends before ordinary relaunch.

Original Iris/options/benchmark settings are byte-equal to the fresh backup
before relaunch; no ordinary-world restore or automation is performed. Benchmark
Mod/marker and physics0.3 are recoverably disabled, physics0.2 restored. Ordinary
0.6 is actually reopened with the matched account and paused at22:10:28:
[native F2](ordinary-restored-paused-native-f2.png), [handoff ledger](ordinary-handoff.json).
Iris regenerates its timestamp comment after relaunch; options/benchmark bytes
remain equal, so no after-launch full Iris byte-identity claim is made. The
ordinary game remains live and paused for the user. No commit/push is performed.

The diagnosis/test-first workflow isolates the fixed near-reflector predicate,
retains the real Iris diagnostic failure and avoids adopting an inactive facet
ablation. See the [independent native audit](independent-audit.json),
[first RED/GREEN audit](native-first-independent-audit.json) and
[actual atlas image audit](ATLAS-VISUAL-AUDIT.md) for bounded conclusions.
The next specific seam is the actual water invocation's raw local-column
decision, vertex unknown flag and upward/downward-face classification. The
broader water/shore/cloud/motion/physical objective remains unfinished.
