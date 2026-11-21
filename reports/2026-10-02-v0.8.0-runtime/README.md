# 0.8 isolated-runtime checkpoint — visual goal still open

2026-10-02. This follows the [frozen native checkpoint](../2026-10-02-v0.8.0/WORK-IN-PROGRESS.md).
The shader/physics candidates remain unchanged: shader ZIP `8fab2af6…`, physics
0.3.0 `958a34a9…`. This is not a release, photorealism acceptance or a new1440p
benchmark. Ordinary play is restored to0.6/physics0.2, with test automation disabled.

## Real connection and observation-tool fix

The exact disposable V2 world/UUID/seed was launched in offline TEST mode with
0.8, physics0.3 and observer0.3.5. The actual game used RTX3080Ti, NVIDIA580.173.02,
OpenGL3.2; the earlier native suite used GL4.6. Its first ocean smoke capture
completed, but explicit observation request `fceb5737…` produced no export while
Mod frames advanced and ready1/known4096 were reported. Those diagnostics alone
were not accepted as real binding/storage proof.

Ranked causes were scope reflection, pass identity and request detection. Pinned
Fabric bytecode identified its package-private `V1ModMetadata`. Parsing the actual
packaged physics bridges through Loader0.19.5 reproduced `IllegalAccessException`
at the production metadata acceptance helper. [RED](cpu/bathymetry-observer-real-metadata-red.log)
was retained before replacing implementation-class reflection with direct calls
through public `ModMetadata`/`Version` interfaces. The same actual-JAR test now
accepts0.3.0 and declines0.2.0/missing metadata; the existing tests/build also pass.
[GREEN/build](cpu/bathymetry-observer-real-metadata-green-build.log).

The changed test-only Mod is0.3.6, SHA256
`dcab3694e264889027c41aae650900f35c3ab0826f0576f0d9b847567352a5c4`.
Old0.3.5 `d2fbe581…` is preserved. Independent bytecode/JAR review found only the
helper, its reflected boundary and version metadata changed;28 other entries,
including Recorder/Mixin/GL-state handling, were identical. This fixes an
observation-tool failure, not a claimed water-rendering or shutdown fix.

Three fresh requests now export the actual pre-draw TRANSLUCENT program421,
named sampler unit5 and existing texture72. Queried storage is64×64 RGBA32F with
nearest/clamp object parameters; Ready/Grid agree with the same-frame Mod state.
The complete64KiB readback must equal the current stored CPU upload before
`available=true`. The11 observer-touched active-unit/binding/PBO/PACK-state fields
are re-queried equal after restoration; this is not a claim about all GL state
or physics uploader restoration. Error flags are not consumed. Effective sampler
object overrides/base-level completeness and final shader-fetch attribution are
not separately observed.

- [Startup request](observations/e4ea1dcc-5ce1-4813-8f5e-e80f6e4ecbaf.json): frame1,
  only4 confirmed columns; all five exported sample points unknown. This is
  binding/readback evidence, not positive depth evidence at those points.
- [Filled request](observations/0ab47dc5-0620-4aa7-9bc6-0d8b3bc259a7.json): frame25393,
  all4096 columns confirmed; every float finite and reserved component zero.
- [Later ocean request](observations/14d72469-96d7-4e2b-9343-136ea1f3750e.json):
  frame54929 after a completed fixed ocean capture; same actual field hash
  `b4c9b5dd0561513fc3c104ff5f8a27039a087f30817bb83cbfd25ad14a4e3ea9`.
  Requests occur outside recorded timing windows. A ready flag is not a claim
  that every column was freshly rescanned on that frame.

JSON/raw files are retained under [observations/](observations/). The observer has
no absolute same-frame camera coordinate or run_id. Consequently matching its
relative origin to a separately recorded static camera remains a qualified
cross-record join, not complete same-frame world-point evidence. None of these
observations alone proves convincing water, physical calibration or FPS.

## Conditional independent saved-floor check

The actual saved V2 Anvil region was decoded read-only, with stable size/mtime
during the read. Assuming ocean camera `(448.5,65.71999988555908,-383.5)` and origin
`(416,-416)`, the five texels map to these real columns:

| Texel X,Z | World X,Z | Saved gravel Y / floor top | Read depth m |
|---|---|---|---|
|32,32|448,-384|45 /46|16.88888931274414|
|31,32|447,-384|46 /47|15.88888931274414|
|32,31|448,-385|45 /46|16.88888931274414|
|31,31|447,-385|46 /47|15.88888931274414|
|40,32|456,-384|39 /40|22.88888931274414|

All five saved top cells atY62 are source water(level0), Y63 is AIR; intermediate
columns contain water and empty-collision aquatic vegetation. Surface62+8/9 minus
the actual floor top predicts all five depths within4.24e-7m. Region
`r.0.-1.mca` SHA at that audit was `ba3d1b065dddf8eeee8977ee011400b8ff58a698b2862a90d9c15fdd8606a755`.
The conditional camera/origin join above is the remaining limitation; no ordinary
save or account contents are included here.

## Actual scenes: the shore is not visually accepted

The [completed ocean/coast run](captures/v08-bridge036-ocean-focused-20261002-1036/)
and [fixed ocean replay](captures/v08-bridge036-frozen-ocean-20261002-1038/) have
actual pose/camera, pack hash, no fallback, native PNGs and raw frame intervals.
The [coast image](captures/v08-bridge036-ocean-focused-20261002-1036/coast-day.png)
still has strong cyan/mint shallows and sharp jagged reflection/refraction bands.
Root inspected it and the older0.6 coast image: the same broad defects are present
in both, but resolutions/phase differ, so this is not a pixel-matched regression
comparison or a measured improvement. Cloud repetition/soft shapes and distant
water bands also remain. Moving-wave/highlight/wake quality is not accepted.

These are1600×900, cap120, VSyncOFF,12/6 chunks,5s warmup+5s observations, not the
project's1440p performance validation. The existing strict `tools/report.py`
correctly rejects1600×900 and was not weakened. [Read-only smoke audit](audit_smoke.py)
uses its PNG integrity and metrics helpers without bypassing that release gate;
[results](smoke-audit.json) validate4 completed captures/2363 intervals, retain
two UI-interrupted aborted runs, and independently check all3 raw fields.
No native GPU test ran concurrently. Observation readbacks are excluded from
timing/visual acceptance. No FPS floor or0.8 visual release is claimed.

## Lifecycle, mistakes and ordinary restoration

The first0.3.5 TEST quit stalled after `Stopping!`; no complete shutdown-save
marker was observed. A diagnostic attach initially used the wrong namespace PID13
(the launcher, not Java27), causing the TEST launcher to exit131. The corrected
Java-target attach produced a thread dump; Java later disappeared without an
explicit TERM from root. This is not a clean-exit success and not a shutdown fix.
No terrain was placed; before/after persisted audits retain390 AIR cells and no
ownership journal. Private launch/thread logs are not published here.

Two0.3.6 camera runs were aborted because a pause/UI screen interrupted them.
Actual X input focus (not merely window activation) resolved the control issue;
pause-on-lost-focus was temporarily disabled only for testing. Failed runs were
not replaced or relabeled successful. X11 screen capture returned a black image,
and Wayland grim capture lacked its protocol: only native Minecraft screenshots
were used as visual evidence.

The later0.3.6 TEST GUI Save/Quit saved all dimensions at10:41:10 JST, reached the
[title screen](lifecycle/test036-saved-title.png), and GUI Quit at10:41:40 exited
Java and its own launcher normally (session exit0, no TERM). One successful GUI
exit does not repair or invalidate the earlier instrumented lifecycle failure.
Saved AIR/ownership audits after save and after exit pass.

Before TEST installation, ordinary play had already saved and exited normally.
A private post-save backup was retained. After testing, `options.txt`, Iris and
benchmark configuration were restored byte-for-byte; the full ordinary-world
directory compared byte-for-byte equal to that backup **before normal relaunch**.
Physics0.2 was restored; observer0.3.6, physics0.3, the enable marker and explicit
observer request were recoverably renamed disabled, not deleted.0.8 remains a
selected-off candidate ZIP, not an ordinary-play upgrade. Launcher window/JVM
settings were retained; ordinary launch/time metadata was not rolled back.

The normal account was then reopened in its existing world without TEST identity,
teleport/time/weather/terrain commands. [Filtered runtime](lifecycle/ordinary-restored-filtered.txt)
confirms0.6/physics0.2/NVIDIA, no active benchmark; options SHA remains
`02516270fea53cc286dceb1d5eca457f2ecc2e0ab6d2e1b15b01c4032307e5f0`.
The [handoff is paused](lifecycle/ordinary-restored-paused.png), debug display off;
Escape resumes. Normal game time/weather evolved naturally during the relaunch;
the pre-relaunch whole-save equality is not a claim that game writes never change.

## Next real requirements

Diagnose the reproduced natural-shore cyan/band behavior from actual receiver,
reflection and lighting provenance; retain physical/occlusion invariants. Add
same-frame absolute-camera/effective-sampler attribution where needed, then
evaluate real moving highlights/waves/contacts and day/weather/dimensions.
Cloud geometry and world-coherent cloud shade still require their own RED/GREEN
and real-scene checks. A new opt-in solar/cloud native probe is CPU-ready only,
not integrated or GPU-run. Full physical/visual goals remain active. Current
implementation and independent review are Codex work, not a new Claude invocation.
