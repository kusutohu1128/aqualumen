I found no blocking defect in the capture, pairing or GL-state path. There are two medium integration findings, both in `tools/water_paired_runtime.py`; both fail safely but can block the handoff. Nothing was edited or run, and no plan file was written: this was a read-only review.

## Medium findings

**M1 — The runtime's GPU-test check can't read the GPU-test receipt that actually exists**
- **Where:** `tools/water_paired_runtime.py:83-88` versus `reports/2026-10-22-joint-paired-water/native-initial/receipt.json`.
- **Reproduction:** `setup --pack <paired.zip> --native .../native-initial/receipt.json`.
  - `setup` expects schema `aqualumen-paired-water-qualification-v1` with the keys `packSHA256`, `compileExitCode`, `nativeExitCode`, `C0Exact` and `classificationPassed`.
  - The receipt has schema `native-paired-water/1` with `paired_zip_sha256`, `build_exit_code`, `exit_code`, `passed`, per-case `c0_byte_equal`, `tested_routes` and `untested_routes: [1]`.
  - `setup` therefore raises "Matching NVIDIA compile/passivity/classification proof missing" before touching anything.
- **Risk:** It fails safely, but none of the reviewed files can pass this check. Whoever writes a translation file by hand could drop `untested_routes: [1]`, and the Minecraft run would then look like it rests on a complete GPU test.
- **Smallest fix:** Make `setup` read the receipt's own schema directly. Require:
  - `passed is True`
  - `paired_zip_sha256 == sha(pack)`
  - `build_exit_code == exit_code == 0`
  - every case has `c0_byte_equal`
  - `set(tested_routes) == {0,2,3,4,5}`
  - `route_assignment_mutant_rejected` and `nonwater_translucent_without_clear_zero`

  Copy `untested_routes` and the receipt's `scope` string into `baseline.json`.

**M2 — Restore can't recover from a half-written test jar or pack**
- **Where:** setup at `water_paired_runtime.py:124-128`; restore guards at `:255-261`.
- **Reproduction:**
  1. Interrupt `setup` while it is writing a test jar or the pack (Ctrl-C, disk full).
  2. A truncated `mods/<test>.jar` or `shaderpacks/Aqualumen-PairedWater-2026-10-22.zip` is left behind.
  3. `restore()` raises "TEST Mod changed" or "TEST pack changed" every time.
- **Effect:** The normal physics 0.2.0 jar stays in the backup folder, so the Lab is left in the test state. That breaks the "converges from partial setup" requirement. The stage-0–4 tests only use complete files, so they don't cover this.
- **Related gap:** `setup` copies the config backups (`:114-117`) but never hashes them against the originals before it starts changing things. A bad copy would only be caught later, by restore, after the originals are gone.
- **Smallest fix:**
  - Write each test jar and the pack to a temporary name in the same folder that doesn't end in `.jar`, check its hash, then `os.replace` it into place. Have restore also move any leftover temporary file with that exact name into the backup.
  - Before the first `shutil.move`, check `sha(backup/name) == sha(GAME/name)` for every config file and for `instance.cfg`.

## Your review points: checked, no defect

- **Production beauty and the actual reflection branch:**
  - C0 blending is unchanged, and `blend.gbuffers_water.colortex12=off` applies to C12 only.
  - The SSR route is classified right after the original `reflectionTrace` (`gbuffers_water.fsh:434`). The receiver route reuses the existing `reflectedReceiver` result and its own branch condition (`:435`). There is no second trace.
  - A non-finite SSR result becomes route 4, as the manifest says.
  - The C12 zero sits before the `discard` (`:263`) and the non-water return (`:266`).
  - `waterFresnel` stays within [0,1], so the strict range check won't trip on real data.
- **Does the time freeze make everything route 5? No.** `frameTimeCounter` still has live uses in the water program:
  - shore foam (`:461`, `SHORE_FOAM` defaults to 1.0);
  - `receiverSolarTransmission` → `cloudSolarTransmission` → `cloudCoordinates` (`clouds.glsl:35`).

  Wave call sites still pass the uniform; only their reads become dead. `ReceiverLightingState.capture` uses whatever program is current, and terrain programs are untouched. This is static reasoning only; the runtime evidence is listed below.
- **FINAL sampler identity:**
  - The C12 unit comes from the active `colortex12` uniform, and the texture is whatever is bound to that unit. No flip state is assumed.
  - The `glGetTexImage` read happens before the quad, and no program writes C12 after the water stage, so it is the same data the quad sees.
  - `aqualumenPairedView` is queried as an active `GL_INT` and must be 0, both before and after the quad.
- **One invocation:** Renderer, pipeline, targets, program, frame, draw FBO, output texture and version, size, the C0/C12 texture IDs and the camera pose are compared before and after (`CaptureRules.same`). The viewport, the current program and the sampler maps are checked again after the quad.
- **GL state:**
  - Every read is wrapped in a save/restore of the active unit, its binding, the read FBO, the read buffer, the pack buffer and all 8 pack settings, and the restore is verified.
  - `beauty()` restores the read buffer that belongs to the target FBO, then the original read FBO's own read buffer.
  - All GL enum constants I checked are correct.
  - No `glGetError` calls and no `glGen*`/`glCreate*` calls.
  - The LWJGL methods and signatures called by reflection all exist.
- **Scope guards:**
  - The config, V2 UUID and pack SHA checks match `CaptureRules.PACK`.
  - `inspectScope` checks integrated server, not LAN, one player, local camera, seed 308060, overworld, no Iris fallback, and physics version `0.3.0`.
  - Exactly five Mod jars by origin, each hash-pinned; the pins match `PINNED` in the runtime.
  - Recorder: `complete`, `stage==1`, a single scene.
  - First-person WATER camera at a fixed pose, daylight 6000 (`doDaylightCycle false`).
- **Restore:** All backup and test-file checks run before the first change. It never rolls back the ordinary save, and it is idempotent.

## Gaps that still need Minecraft evidence

1. **First use of reflection lookups.** No earlier probe has read `field(renderer,"pipeline")` or `field(renderer,"renderTargets")` on `FinalPassRenderer`, nor `iris$getColorBufferVersion`, `field_1482` or `field_1481` (`PairedObserver.java:145-155`). A wrong name writes a failure manifest and uses up one of the 4 requests allowed per JVM. Running `javap -p` on the pinned Iris jar first would rule this out.
2. **Pack actually active:** a `run.json` with `shader_active` true and `shader_fallback` false for this pack's SHA; no `getStoredError`.
3. **Receiver source producer actually live in this launch:**
   - the `[Aqualumen Receiver] lighting-captured … cloudTime=` log line;
   - `source-runs-updated … ready=2`;
   - and either `routeCounts[2]+[3] > 0` or an explicit explanation if only route 5 appears.

   `collect` only requires routes 1–5 to sum above zero, so a capture that is all route 5 would still be archived.
4. **Route 1 (SSR) has never been tested on the GPU.** Any route-1 pixels in the first capture are untested evidence, not a pass.
5. **Iris applying the per-buffer blend override on the Sodium water path.** The GPU fixture set the blend state itself. Underwater records write alpha 1, so they come out exact either way; only the "non-water translucent surfaces reset C12" caveat depends on the override.
6. **Pixel alignment of C12 and beauty.** Both raw files are read bottom-up, and the pack's `fullscreen.vsh` passes `gl_MultiTexCoord0` through, so they should line up. But the `aqualumenPairedView≠0` preview path never ran, so alignment isn't proven. An offline check that water-mask edges coincide with edges in the beauty image would settle it without code changes.
7. **Successful capture end to end:** a manifest with `available`, `beforeReadStateRestored`, `afterReadStateRestored` and `quadInvocationReturnedObserved` all true; NVIDIA renderer; 1600×900; file hashes matching. Then `restored.json` with all four exactness checks true after quitting.

## Points to flag in the handoff

- **This is not shipped production.** The captured beauty is the production post-process applied to a scene with waves frozen at 17 s and ripples off, so it matches the control pack, not live 0.6 output. The run also uses physics `0.3.0-plant-owner-probe-v100`, not the normal 0.2.0, so the route mix reflects the test producer. Don't quote route counts as the shipped 0.6 + physics 0.2 behaviour.
- **Pass level so far:** The GPU result is a compile/link and C0-equality test on generated fixtures. It covers neither Iris resource binding nor Minecraft. Native route 1 and the `FINAL preview≠0` path are untested. A single Minecraft capture would prove pairing for one frame, not a visual or physical acceptance.
- **Lab leftovers:** The run leaves files in the Lab that restore doesn't touch: runs under `aqualumen-benchmark/`, the `paired-water-observations/<uuid>` folder, `status.json`, and gamerule/time changes in the V2 save. These are authorized, but they aren't covered by `restored.json`.
- **Fail-closed but silent:** If the scope check or Recorder check never passes, the observer writes nothing at all. `collect` then only reports "Capture not ready", and the reason has to be read from the logs.
