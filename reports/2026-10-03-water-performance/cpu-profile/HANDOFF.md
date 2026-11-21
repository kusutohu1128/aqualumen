# CPU profiler handoff

READY for root-owned matched TEST runtime, not runtime/GL or performance acceptance. No original source/JAR, shader, optics, permission policy, or installed instance was edited by this work. No GL/game/API operation occurred.

## Artifacts and modes

Both JARs are in `pair-v1/`; `pair-repeat-v1/` independently rebuilt identical bytes.

- `aqualumen-benchmark-0.3.9-profile-v1.jar`: SHA-256 `3304886b54c98181cf9db28c9852be15cee9c54df3463998a6d11a96b3f980de`
- `aqualumen-water-sun-test-0.1.0-profile-v1.jar`: SHA-256 `66fe926bd1e8339e3520fc46f7e12994378fc12a8603a5c990b9dd1d69730920`
- `pair-v1/manifest.json`: SHA-256 `46a3594d1aa39ab6d4590aca97096cb8ab3886756fd24526a564cac03d37f3b3`

Install/restore is root-owned. These replace, not coexist with, the corresponding original same-ID/version TEST JARs. Resources/dependency versions remain unchanged. Use the same two generated JARs and frozen zero-physical shader ZIP in both runs. In the existing benchmark properties, set exactly `sun_profile=control` or `sun_profile=profile`. Missing property defaults to control; any other value disables available profiling rather than changing authorization. Mode is read once per accepted benchmark run, after the original setup guard.

Control executes the same wrapped original supplier and full hash, with profiler clocks/counters off. Its report has `timingsMeasured:false`, counts/timings null, and no measured rows. Do not call control zero-overhead relative to the original binaries; it retains the wrapper/function/lambda overhead. Profile additionally measures/counters. Keep all observer request files absent during measurement.

## Scope and output

Only four source spans in three generated files differ from 24 pinned original source/resource inputs: supplier wrapping in SunUniforms, complete original hash-expression wrapping/identity array observation in BathymetrySnapshot, and setup/finished callbacks in Recorder. `recover` reverses them to exact original bytes; `parents/` and `sources/` archive both. Frozen SunAuthorization itself is unchanged. The build rejects altered parent/dependency pins and existing outputs.

The supplier receives an immutable registration ID once. Profile reads the actual live Iris COUNTER and the current private Recorder.state via immutable reflected handles at each invocation before the original delegate. It does not infer phase from the previous render tail. The original delegate/hash execute exactly once. Observation failures make metrics unavailable without changing original return/exception; an original Error is not swallowed. No authorization/hash/config/world/pipeline/physics-result cache exists.

Output is `runDir/sun-profile.json`, created once with CREATE_NEW after original complete.json/cleanup and state=complete, before optional autoQuit. There is no per-call I/O or console output. Failed exports do not change benchmark completion or permission. Bounds are 4096 aggregate rows and 256 registration IDs; overflow preserves every original check and makes metrics unavailable. Nested suppliers also make attribution unavailable, rather than silently double-counting an accepted total.

`totalAuthorizationNs` times the original supplier interval with some observation/wrapper overhead. `fullHashExpressionNs` includes getInstance/readAllBytes/digest/hex/equals plus observation; it is NOT isolated SHA time and is contained in the supplier total, not an additional total to add. Bytes are the length of the exact one readAllBytes array passed unchanged to the original digest. `hashCalls` includes attempted owned expressions, including failures; missing metadata/overflow must not be interpreted as zero cost.

Unowned hash fields cover instrumented ReflectedBoundary.scope expressions outside a supplier context. Recorder's separate setup/finish `hash(Path)` is intentionally unchanged and unmeasured; its regular warmup/sample guard(false) does not hash. All phases before completion are present. Filter sampling rows before computing sampling-only attribution. A first sampling boundary is discarded by Recorder's interval recorder; do not assume all phase=sampling rows automatically match timings.csv intervals one-for-one. Actual runtime row/phase/frame qualification remains root/auditor-owned.

## CPU checks completed

- Five public Java PASS summaries, compiled and run against the actual generated JARs: real frozen authorization with synthetic external live scope; fresh same-frame1->0->1; injected clock/frame/phase/end-clock failures; original Error/Exception identity; real temporary-file hash and same-size mutation; array identity; unowned separation; actual entry-phase/frame fixtures; counters-off control; finish-only/no-repeat export; 4097 fresh checks through row overflow; export failure isolation.
- Four public Python builder tests PASS: exact parent recovery, altered source refusal, existing-output refusal, exact hash-data/boolean expression recovery.
- Actual pinned Iris/compiled-Mod CPU routing PASS (`addDynamicUniforms`); runtime mixin/GL unverified.
- Two independent Java21 builds, no compiler warnings; both JARs byte-identical.
- An independent reviewer fully read the bounded source route and reported no startup blocker. Their review did not execute additional runtime/GL tests.

API/construction RED logs are retained and are not optical or performance regression findings. CPU tests substitute external Minecraft/time boundaries, not the profiler internals. Temporary-file hash tests are not execution of the actual Minecraft ReflectedBoundary.scope route; source-contract checks and root's runtime close that boundary.

Final owned source SHA-256 pins:

```text
d31a4d8dc52a042410e9e076fbe8333f0d400928f76615c79004215eff36bba2  tools/water_sun_profile_build.py
b0b02810fc744043c1a266ec9269efea975fac2566f6b53be81a7b2efe3e20d7  tools/test_water_sun_profile_build.py
8f87eb0a0ba2f0e9ad2f719eb3737047abed890ca69cbc926864d0286301436d  tools/water-sun-profile-mod/dev/aqualumen/bench/SunPerformance.java
91f8b4ace6a0d058798a0255ef5bc05fdf16549923facebab3d3ae6f00eb8f33  tools/water-sun-profile-mod/test/dev/aqualumen/bench/SunPerformanceTest.java
```

No speed-up, FPS cause, numerical relaxation, visual adoption, or whole-goal completion is claimed. All owned writes stop after this receipt and final checks.
