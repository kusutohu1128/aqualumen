# 0.8.2: receiver-local cloud-light correction, development checkpoint

The source defect is corrected and verified in qualified production-main tests;
the full natural-water/sunlight goal is **not complete**. Actual coast/river stills
retain cyan/mint and jagged dark bands; cloud morphology remains artificial.
This candidate is not promoted over ordinary0.6/physics0.2.

## Genuine RED / GREEN

Actual prepare→original terrain VS/FS→original deferred main runs on RTX3080Ti,
NVIDIA GL4.6. Fixed phase120, zenith world Sun, P=(0,63,0), Q=(-64,63,0), eyes
at receiverX±64/Y127, white albedo, normal up, fully lit fixed world shadow.
Actual queried C6/C7/C5/C8 storage is16F, C0/C4 and passive inputs32F.

The earlier huge-quad trials fail geometric qualification and remain
INCONCLUSIVE. The qualified one-pixel receiver preserves original VS/FS and
constant1x1 white/shadow textures; C5 has no screen derivatives. It verifies
receiver shading, not broad terrain rasterization. Inputs and positive distinct
cloud columns are qualified from actual prepare before any terrain C5 draw.

| Fixed receiver, red C5 | Old eye A / B | Corrected eye A / B |
| --- | --- | --- |
| P | 5.203125 / 5.3359375 | 5.3359375 / 5.3359375 |
| Q | 3.76953125 / 5.3359375 | 5.203125 / 5.203125 |

Old Q changes approximately41.55% relative to the first eye despite the same
world point; the camera-site cloudy cache tracks it. Corrected eye difference
is0 on both receivers in every RGB channel. Each absolute C5 lies within the
prepare-derived `(SOLAR/PI)*observerClearC7*(receiverC6/receiverC7)` interval.
Both16F numerator/denominator errors, observer clear precision, target storage
and declared binary32 allowances are propagated; no aesthetic tolerance or
output-driven receiver search is used.

P/Q red source difference remains0.1328125 against the independent model-source
expectation0.131696408/bound0.012735542; all RGB channels have resolved positive
spatial response. Deleting cloud extinction cannot pass this control. This is
procedural source consistency, **not independently solved exact cloud depth**.
Whole C0/C5 passive-observer and repeat differences are0. Original deferred C8
retains positive actual terrain C5, writes zero sky RGB and stays unchanged
after a verified distinct C5 overwrite. Actual source snapshots/raw arrays are
in [native evidence](native/evidence.tgz); the [final source/harness](native/source-and-harness.tgz)
preserves the code used. [RED](native/red-qualified-field.log),
[gated GREEN](native/green-gated-field.log) and
[full retained native suite](native/full-native-final.log) are directly readable.
The retained nonzero-wave first-bed source response also passes unchanged.

## Source and model scope

Cloud integration now takes an explicit world-XZ origin. Terrain, foam and water
glint evaluate the receiver's own column; sky rendering keeps its original
observer-column overload. Clear atmosphere remains the observer-altitude C7
approximation. Cloud tangent geometry, weather closure, morphology and other
scatter/aerial paths are not calibrated by this slice. Missing/incompatible C7
retains a legacy initialization/diagnostic fallback; legacy native callers taking
it are not evidence of the new path. Real named-C7 sampler/cache pixel readback
is not recorded; actual Iris C6/C7 allocations are observed below.

Zero-direct receivers and zero-foam pixels skip unnecessary cloud integration.
No extinction/color coefficients or refraction march changed. Per-fragment32-step
integration still adds cost; a qualified world-grid shadow cache is a useful next
performance step, not implemented here.

## Real Minecraft and performance

[Three completed views](captures/v082-cloud-local-smoke-20261002-1503/run.json)
activate exact0.8.2 without fallback, Minecraft1.21.1/Iris1.8.8/Sodium0.6.9,
physics0.3.0 and observer0.3.7. Exact disposable V2 world UUID
`b22dbccb-2970-41e6-847f-f183b1ec923d`, vanilla seed308060, no terrain placement.
Minecraft records NVIDIA GL3.2, distinct from native GL4.6. Actual main/alt C6/C7
allocations are RGBA16F1024x512 with restored observation binding.

Each focused1600x900 view warms20s and samples5s, cap120/VSyncOFF, 12render/6sim.
The [raw-data audit](smoke-audit.json) recomputes1263 positive integer-ns intervals
totalling14,991,900,099ns, validates all3 PNGs and identity/camera metadata.

| View | Mean FPS | 1% low FPS | Worst ms |
| --- | --- | --- | --- |
| Coast | 94.415 | 74.965 | 14.347 |
| River | 91.068 | 70.378 | 14.914 |
| Ocean | 67.248 | 53.007 | 20.212 |

Ocean has52 intervals slower than16.667ms; no60-FPS floor,1440p result,
new-chunk/long-run guarantee or controlled timing A/B is claimed. The strict old
FPS target was relaxed, but this cost is not hidden. [Visual audit](VISUAL-AUDIT.md)
does not accept natural-shore/cloud appearance or motion. Offline TEST logs also
contain auth401 and unavailable OpenAL-device warnings, not shader errors; no
authentication/audio fix is claimed.

## Artifact and lifecycle

- ZIP `Aqualumen-0.8.2.zip` SHA256
  `6f555c5b8fbb30531d2638cd69997f2969ed18bff1695165e3fc6622007199e5`.
- Water FS `b21d9e5a9d3353dd9c3803db5d9591725e12f9c843b124f2039ee0fbbd06e869`.
- Clouds `9f4a12842dbae37788d2be89418462b0780c169b63298c77a2158aa39ead14b9`.
- Lighting `34f2c051f07a0c8ed2bb1be0a6a8481a54e2b576a99ded143fc5b9b8cba2de48`.
- Cloud harness `5e6eeeca62aec60d03613ccfd51911daa10c9348ccb20af4e0dd799d40ed0f73`.

Old0.8.1 ZIP SHA remains unchanged. All native GPU jobs finish before Minecraft
launch; no GPU test overlaps timing samples. Implementation and independent
team review are Codex work, not a claimed Claude invocation.

TEST Save/Quit stalled after player disconnect. Only the freshly revalidated TEST
Java and its own launcher received TERM; session29020 ended143 and both processes
were subsequently absent. This is not a clean exit or a fix of that shutdown defect.
The bounded saved-world audit finds all390 reserved cells AIR and no pending
fixture journal before/after stop, not whole-world/entity integrity. Original
options/Iris/benchmark properties are byte-equal to their pre-test backups;
0.6/physics0.2 is selected and candidate/benchmark controls are recoverably
disabled. Ordinary saved files still match the fresh post-user-play backup;
the ordinary world was not restored or automated. See the
[prelaunch restoration ledger](lifecycle/restoration-before-normal-launch.json).
No fresh ordinary paused handoff is claimed until actually observed.
The full goal remains active. Next high-value water step is the independently
qualified [receiver-Sun radiance-unit tracer bullet](../../docs/reviews/codex-water-sun-radiance-plan.md),
then natural shore/cloud shape and temporal/contact appearance. Do not substitute
this narrow source correction for the desired end state.

## Later ordinary-handoff addendum

After the subsequent0.8.3 validation, ordinary0.6/physics0.2 is actually reopened
and paused at2026-10-02T07:24:09Z. The
[later handoff ledger](../2026-10-02-v0.8.3/lifecycle/ordinary-paused-handoff.json)
and [native image](../2026-10-02-v0.8.3/lifecycle/normal-restored-paused-native-f2.png)
prove that later point, not a retroactive clean0.8.2 TEST shutdown. The prelaunch
restoration checkpoint above remains historical; the full visual goal is open.
