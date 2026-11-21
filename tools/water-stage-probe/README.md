# TEST-only terrain tessellation stage observer 0.1.0

CPU implementation/build only until root explicitly runs the isolated test. It depends on the immutable benchmark 0.3.9 projection-guards JAR and exact Iris 1.8.8 / Sodium 0.6.9 / Minecraft 1.21.1, with candidate physics 0.3.0. It is not a renderer or a shipping Mod.

The constructor saves the actual program id, pipeline and `containsTessellation` argument: the pinned `SodiumShader` has no `getHandle()` method. At `setupState` TAIL the observer only admits a request when that argument and the actual `ImmediateState.usingTessellation` are true. A solid setup does not consume the request. The actual active pipeline must match the constructor object.

Root may place this opt-in request only after measurement has completed:

```properties
# config/aqualumen-water-stage-observe.properties
world_id=b22dbccb-2970-41e6-847f-f183b1ec923d
request_id=<new canonical lower-case UUID>
include_sources=true
```

The existing `config/aqualumen-benchmark.enabled` marker and exact schema-2 benchmark configuration/selected ZIP SHA are also mandatory. Both properties inputs are bounded to 16384 bytes and opened without following symlinks. The canonical path must be the `instances/Aqualumen Lab/minecraft` directory; the reused public benchmark guards additionally require the approved V2 UUID, seed 308060, actual saved natural-world marker, local private integrated server, one player/local camera, active expected pack with no fallback and physics 0.3.0. Ordinary world/disabled marker/not-using-tessellation cannot reach a GL read. Active benchmark phases are rejected before GL; only idle/complete/aborted are eligible.

There are at most eight canonical, one-shot eligible attempts per JVM, at least one second apart. An eligible failed GL observation consumes its request as well. A request ignored before eligibility does not. Inputs are never deleted or modified. Only the authorized immutable output is created:

```text
aqualumen-benchmark/water-stage-observations/<request UUID>.json
```

The observer reads the current program (which must equal the constructor id), link status, bounded attached shader ids/types, both patch arities, actual GL version/renderer and ARB/core tessellation capabilities, then checks program/frame again. All four VS/TCS/TES/FS types, link success and both arities 3 are required. Optional requested shader sources are bounded to 256 KiB per stage and exported as SHA-256/byte count only; the TES identifier marker flag is substring evidence, not a value-transport proof. Missing APIs or incomplete/changing observations are unavailable. Exceptions contain only the class, never their messages/paths.

No GL writes, binds, resource creation, texture reads or `glGetError` occur. This observes **linked terrain tessellation stages**, not exclusive water identity, a draw, TES invocation count, C12 fragment data or natural visual acceptance. Program/frame equality is not proof of every GL state. It complements (rather than replaces) root's actual C12/no-fallback stage-transport check. Native Iris execution remains unverified until that future test.

Build without installing: `bash tools/build-water-stage-probe.sh`. Existing output is never overwritten. CPU RED/GREEN logs and final build log are in `reports/2026-10-03-water-tessellation/observer-*-cpu-*.log` and `observer-build-cpu.log`. Test data is explicitly synthetic; CPU PASS is not GL evidence.
