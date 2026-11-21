# Performance NEXT: separate guard cost from shader cost

Status: proposal only. This CPU review implemented no Mod, shader, optical policy, cache, or instrumentation; it performed no GL or Minecraft operation. Root owns runtime/GPU work. The next experiment must retain the frozen support certificate, stable inverse, 48-node rule, source accounting, reconstruction/receiver checks, unknown rejection, and whole-result fallback.

## What the existing timings establish

The near-view diagnostic runs recorded 12.966904488832608 FPS for reject-reasons (64 frames) and 12.558993853044617 FPS for zero-reasons (62 frames), after 10-second warmup and approximately five-second sampling, at 1600 x 900. These are `System.nanoTime` render-tail intervals for the whole client, not GPU stage timings. They do not identify FP64, integer certification, ZIP hashing, or any other component as the cause of the low FPS or the difference. They also compare different optical work/outcomes and diagnostic packs, not one isolated performance variable.

Sources: `iris-reject-reasons/run/underwater-up-near.json`, `iris-zero-reasons/run/underwater-up-near.json`, and their `run.json` files in this packet. Native correctness captures contain no accepted FPS measurement. A native fixture's future GPU timing would not become Minecraft FPS.

Root explicitly confirmed that every completed measurement started with no active observer request files. Observer requests were written only after run completion, then moved closed before exit/next configuration. This includes the latest completed reject-physical three-view measurement; zero-physical continuation was pending when this proposal was requested. The potential retained-request overhead below is therefore a future protocol warning, NOT an explanation of these completed measurements. The CPU reviewer did not independently replay root's file-movement protocol.

## Verified static cost seam

1. `tools/water-sun-test-mod/dev/aqualumen/suntest/mixin/SunUniformMixin.java:12` registers at `CommonUniforms.addDynamicUniforms` TAIL. `SunUniforms.java:12-17` registers an `IntSupplier` with `PER_FRAME`; `SunUniforms.java:13-14` constructs and evaluates fresh runtime authorization on each invocation.
2. `SunAuthorization.java:23-44` freshly checks canonical Lab paths, opt-in files, bounded configuration, selected archive metadata, and the exact saved-world marker. `SunAuthorization.java:63-69` then evaluates the live scope and returns zero on exceptions or unavailable APIs. Success is not latched.
3. `tools/benchmark-mod/dev/aqualumen/bench/BathymetrySnapshot.java:231-267` freshly queries live Minecraft/Iris/physics state on the render thread. At lines 260-261, a matching active pack with no fallback/error causes `SHA-256(Files.readAllBytes(selected ZIP))`. This allocates and reads the complete ZIP each qualifying scope invocation; it does not cache the digest.
4. Actual installed ZIP sizes observed during this review were 221,304 bytes for reject-reasons, 223,709 bytes for zero-reasons, and 233,866 bytes for zero-physical. These are approximately 216-228 KiB, NOT near the 16 MiB authorization bound. Physical filesystem reads versus OS page-cache service and their costs were not measured.
5. Pinned Iris bytecode confirms `ProgramUniforms.lastFrame` is an instance field. `ProgramUniforms.update()` executes that instance's `perFrame` list when its frame differs from `COUNTER`, not globally once for all programs. The initial `once != null` branch also executes `perFrame` but does not set `lastFrame`; another update in that initial frame can therefore repeat it. Actual active-uniform/program counts are unmeasured; registration alone does not prove every program invokes this supplier.
6. `IntUniform.updateValue()` calls `IntSupplier.getAsInt()` before comparing `cachedValue`. Its cache avoids redundant GL uniform writes, not authorization evaluation.
7. `Recorder.java:818` periodically calls `guard(mc,false)` during warmup/sampling; `Recorder.java:178-182` hashes only when `checkHash` is true. Its setup/finish hash calls must not be misreported as this per-frame hot path.
8. `SunGuardObserver.java:31-34` performs authorization when a bounded request file exists, before benchmark-phase and destination/request-consumption checks at lines 41-47. A retained request can add a full hash at most once/second even if no capture occurs. The absent-request measurements above exclude that path, although the ordinary bounded filesystem poll still exists.

The installed benchmark and Sun Mod bytecode were inspected as well as the checkout sources. Iris bytecode inspection used the local pinned Java 21 `javap -p -c`, on `net.irisshaders.iris.gl.program.ProgramUniforms` and `net.irisshaders.iris.gl.uniform.IntUniform`. In the former, the initial branch updates `perFrame` at offsets 47-52, while the regular instance-frame comparison/update is at offsets 94-119. In the latter, supplier invocation is at offsets 0-9 and cached-value comparison/write follows at offsets 10-31. No bytecode execution or GL was needed.

## First experiment: one instrumentation change, no optimization

Use the same frozen zero-physical pack for all comparison runs. Add only bounded aggregate profiling around the existing authorization path, preserving call order, every live check, every full hash, exceptions, and returned permission. Record supplier calls and authorized/rejected results, hash calls, bytes read, total authorization nanoseconds, and separately hash nanoseconds, grouped by actual Iris frame and supplier/program identity. Distinguish normal uniform suppliers, setup/finish validation, and observers. A source pin and the installed Mod's binary pin must identify this TEST-only instrumentation.

Do not write files or print per call while sampling. Export aggregates after completion; measure/report timer-and-counter overhead with matched instrumentation controls. Use repeated matched runs with fixed world/camera/time, resolution/options, current pack/pipeline, JVM/GC configuration, and no active observer requests. Record GPU conditions rather than assuming identical clocks/temperature. Do not subtract a single physics-update snapshot from whole-frame timings. This experiment asks how much render-thread time the unchanged guard consumes, not whether a cache improves FPS.

If GPU attribution is then required, make it a separate experiment. Place an asynchronous timer around the actual water draw, excluding uniform/scope checks, readback, and output. In the existing native chain, the draw seam is `sunProbe::draw` in `tools/water_residual_sun_probe.cpp` at `glDrawArrays(GL_PATCHES,0,6)`, called through the actual-main capture chain. Timers enclosing `prior::capture` or its `glReadPixels` would conflate rendering and observation. Root alone performs GL work. Native timing remains a qualified fixture measurement, not whole-client FPS or an isolated FP64 diagnosis.

## Possible later single optimization, not authorized or implemented here

If profiling supports it, first consider memoizing successful immutable reflection member lookups, keyed by actual class/member/signature, while reading fresh objects and live values every invocation. Do not memoize authorization, world/player/camera/pipeline, physics metadata results, configuration/markers, file contents, or hash results. Unavailable APIs must still fail closed; do not latch failures or retain an authorized result across Mod/world/pack changes.

Per-frame permission caching and digest caching keyed only by path/size/mtime are NOT equivalent to the current invocation-time checks. Same-size ZIP edits with restored timestamps, same-frame marker/config mutations, replacement/symlink races, pack reload/fallback/error, world transitions, LAN/player/camera changes, and physics/API invalidation must revoke permission rather than reuse an earlier success. An immutable pack-generation snapshot alone does not detect later mutation of the installed source file. Hash memoization would need a separately declared stronger mutation protocol and proof; no such proof is supplied here.

Before any eventual cache experiment, public fail-closed tests must cover those transitions, including changed ZIP bytes with equal length and restored mtime, removal/restoration of opt-ins, config/marker changes, symlink/path replacement, exceptions, and physics or pack invalidation between supplier invocations in the same frame. Preserve optical outputs/classes/source ledgers and fallback behavior. A speed improvement cannot authorize safety or numerical-policy relaxation.

## Pins used by this review

All hashes below are SHA-256. Paths are relative to the repository except installed binary basenames, which were read in the canonical Aqualumen Lab `minecraft/mods` directory.

```text
e22b57d9f840eeb9198cfa40d9801bd63aabb993b3ed3087885e98634461ddba  tools/water-sun-test-mod/dev/aqualumen/suntest/SunAuthorization.java
0cc67b0cd0a49ef42192dd5a6d8cdeb2fafdcbfbbb4bd4495f225d92e8f258e3  tools/water-sun-test-mod/dev/aqualumen/suntest/SunUniforms.java
ba64fd03abfe847c686a31c30dd9543ad5ba6ad9a3d133f335cef34692450951  tools/water-sun-test-mod/dev/aqualumen/suntest/mixin/SunUniformMixin.java
b91bd97e61a48ba08028028c9c39ec20d1fb8eaf446c96b18c66bf24ac18ad67  tools/water-sun-test-mod/dev/aqualumen/suntest/SunGuardObserver.java
38a27b286e74816e0d009353218200ba70c3fb6a86b117e5e3f442e974b591b8  tools/benchmark-mod/dev/aqualumen/bench/BathymetrySnapshot.java
98dc953802ed850efe6e0b8704a0d90236647346c939bd171ac2f934b2e3e678  tools/benchmark-mod/dev/aqualumen/bench/Recorder.java
6ad20599ecd495605b9f490a758c7e9daa625de119276c7f881467352c655687  tools/water-sun-test-mod/test_uniform_route.py
b5ad39a6cb113ca0a1765f06689f9f4b29ccd0c81247de90b06c42f5da1092f5  iris-fabric-1.8.8+mc1.21.1.jar
e942f1a193e1a1f5875cd5041a59b67e88414655b124ec8fd5ae2d721ec8edaf  aqualumen-water-sun-test-0.1.0-observer-v2.jar
ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29  aqualumen-benchmark-0.3.9-projection-guards.jar
6e5b3374c9de73f97cf49fb22052c55d378d0a3c4602d0b3128bbc12dc65597f  reports/2026-10-03-water-sun-support/iris-reject-reasons/run/underwater-up-near.json
9baf8f017146e667c46c5da4ef7a51ad8eb5a22404b29d668081c01d12d5c527  reports/2026-10-03-water-sun-support/iris-zero-reasons/run/underwater-up-near.json
8e2d0b80a11735ed46dd309aa11fe76e053f06c6e606354b762e12406f7c93b5  reports/2026-10-03-water-sun-support/iris-reject-reasons/run/run.json
24c0e4556e899090c0877cc917cb06a7059402ae52a023e281b3fc04a20326c8  reports/2026-10-03-water-sun-support/iris-zero-reasons/run/run.json
```
