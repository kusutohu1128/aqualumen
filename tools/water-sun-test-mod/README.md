# TEST-only Sun gate and prepared-uniform observer 0.1.0

CPU implementation only until root explicitly installs and runs the disposable TEST. No optical policy, game command, texture operation or GL write is implemented here. Iris performs its normal uniform upload using this supplier.

The sole registration is `CommonUniforms.addDynamicUniforms` TAIL, inherited `UniformHolder.uniform1i(PER_FRAME,"aqualumenSunTestAuthorized",IntSupplier)`. Actual Iris 1.8.8 bytecode shows Sodium water uses this dynamic registration path, not `addNonDynamicUniforms`. The supplier reevaluates real filesystem and live Minecraft scope on every invocation, including warmup/sampling, and never retains a successful value across world/pack switches. Failure returns 0 without exception messages or paths.

Authorization requires BOTH regular, bounded opt-in files:

```text
config/aqualumen-sun-test.enabled
config/aqualumen-benchmark.enabled
```

The canonical directory must be `instances/Aqualumen Lab/minecraft`. Config/world-marker reads are NOFOLLOW and at most 16384 bytes; directories must resolve identically, the installed ZIP must be non-symlinked and at most 16 MiB. Existing schema-2 `aqualumen-benchmark.properties` must select an exact SHA-pinned `Aqualumen-ShoreProbe-world-*.zip`. The real saved `AqualumenNaturalV2` marker must have schema 2, UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`, seed `308060`, noise-overworld generator. The pinned benchmark guard freshly verifies actual save path/seed, private integrated/non-LAN server, one identified local player/camera, Overworld, active selected ZIP/hash/no fallback/error and physics 0.3.0. Missing marker/unknown APIs fail closed. Full installed ZIP hashing is repeated by the reused guard; that CPU/I/O overhead belongs in BOTH matched timings. PER_FRAME suppliers are per program, not globally once per frame.

Root may request the one-shot observer only after measurements complete:

```properties
# config/aqualumen-sun-guard-observe.properties
schema=1
world_id=b22dbccb-2970-41e6-847f-f183b1ec923d
request_id=<new canonical lowercase UUID>
```

At the actual `SodiumShader.updateUniforms` TAIL, only a constructor-identified TRANSLUCENT tessellated program with the current IrisRenderingPipeline, fresh guard=1 and Recorder idle/complete/aborted is admitted. It reads the current program, Iris frame and exact active scalar GL_INT uniform (type5124,size1,value1), then verifies program/frame unchanged. No binds, GL writes, glGetError, texture reads or resource creation occur. All failures are unavailable, not guessed success. It creates immutable `aqualumen-benchmark/sun-guard-observations/<UUID>.json`; at most eight eligible one-shot attempts/JVM, at least one second apart. An eligible failed capture consumes the UUID. Inputs remain untouched. Never leave new observer requests pending during timing.

Schema `aqualumen-sun-guard-observation-v1` exports `constructorProgram`, `programBefore/After`, `frameBefore/After`, `programAndFrameUnchanged` and nested `uniform={name,active,location,type,size,value}`. Exact world, pack SHA, versions, pipeline and supplier paths accompany it. This proves only a prepared current uniform—not an exclusive water draw, fragment fetch, WNS requested/applied, per-node optics, full GL state equality, or the screenshot's same frame. Actual WNS telemetry requires a separate same-main STORE pack/readback; the later captures are not assumed simultaneous.

Build without installation: `bash tools/build-water-sun-test-mod.sh build/aqualumen-water-sun-test-0.1.0-NEW.jar`. Existing artifacts are refused. The benchmark compile dependency is pinned to SHA `ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29`. Four Java CPU suites exercise public boundary behavior; a separate `test_uniform_route.py` checks the actual pinned Iris bytecode against the compiled Mod target. CPU/mixin routing evidence is not actual Iris/GL execution or natural visual acceptance.
