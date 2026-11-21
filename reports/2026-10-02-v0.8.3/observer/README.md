# Benchmark 0.3.8 solar-cache observer: CPU freeze

This packet freezes the candidate benchmark source, its already-built JAR and CPU evidence. It does **not** contain a real Iris/OpenGL observation or establish rendering quality. No game, GPU, world, configuration or installation action was performed to create it.

- `aqualumen-benchmark-0.3.8.jar`: `ac8ffea8e062130c527961d10287f9a76c7cf21ee600edecb7ec01c9a155a499`.
- Preserved `aqualumen-benchmark-0.3.7.jar`: `e89739cb92f65d55309187fc2e58f8e4cfaeb3395167c9fb1b37b39299d045dd`. Its original build file remains unchanged.
- `benchmark-source.tgz`: complete benchmark Java/test/config sources, builder and three Python test dependencies. This contains no saved world or account data.
- `benchmark-0.3.8-build.log`: 11 Java suites and 30 Python tests passed. The two `*-red.log` / `*-green.log` pairs preserve genuine CPU behavior failures followed by passes, not shader/GPU RED/GREEN evidence.
- `SOURCE-SHA256SUMS` records individual source bytes; `SHA256SUMS` records this packet's files, excluding itself.

The archived builder uses the existing Java 21, Fabric Loader 0.19.5 and Mixin 0.8.7 dependencies. Its packaged-metadata boundary tests also require physics JARs outside this archive: 0.3.0 SHA256 `958a34a9195f260921a43ea296a4968ef691339aac2b038129702d4ca572a310`, and 0.2.0 SHA256 `1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e`. A rebuilt JAR may differ in archive timestamps; the frozen JAR above is the runtime identity.

## One-shot request

Only the lifecycle owner may place the following in the dedicated TEST instance's `config/aqualumen-solar-cache-observe.properties`, after frame sampling is complete:

```properties
schema=1
world_id=b22dbccb-2970-41e6-847f-f183b1ec923d
request_id=<new canonical UUID>
pass=TRANSLUCENT
```

`TERRAIN` or `TERRAIN_CUTOUT` is also supported, one pass per fresh request UUID. The separate benchmark config must select the expected ZIP and its actual SHA. Output is immutable `aqualumen-benchmark/solar-cache-observations/{UUID}.json`. The observer never deletes or modifies the request. It allows at most eight authorized attempts per JVM and polls each pass at most once per second.

Before any GL query, guards require the enabled marker, exact AqualumenNaturalV2 UUID/seed 308060, Overworld, private integrated server with one identified local player/current camera, expected selected ZIP bytes/no fallback, physics 0.3.0 and the current Iris pipeline. Only Recorder states `idle`, `complete` or `aborted` permit capture. An authorized request encountered during active measurement/lifecycle phases records failure once; use a new UUID later, not an automatic retry. Normal worlds remain GL-inert.

## Evidence and limits

At the pinned Iris 1.8.8 `SodiumShader.setupState` TAIL, the observer validates the actual current program and active named scalar C7 sampler, its assigned unit/bound texture and existing target7 main/alt identity. It checks actual RGBA16F/level0/base0/1024x512 storage and distinct C6 source identity. A single bounded 8 MiB GL3.2 readback exports only C7 `(0,511)` and `(1,511)` as exact float values. All eleven active-unit/PBO/PACK caller-state fields are restored and independently re-queried; failed restoration invalidates the result. No texture, program, framebuffer or sampler binding is changed, and GL error flags are not consumed.

Runtime acceptance requires `available=true`, `stateRestored=true`, actual C7 metadata and the two valid texels. Solar RGB must each be finite, positive and at most 1; alpha is 1, and the neighbour is black with alpha 1. Therefore daytime is required for the planned positive-cache proof: legitimate night/underflow zeros are rejected rather than represented as missing sunlight.

This proves prepared input connection and cache contents, **not** that a particular fragment executed a fetch or that the cache was produced in the same frame (`shaderFetchExecutedProven=false`, `cacheWrittenThisFrameProven=false`). `timingAcceptanceExcluded=true` and `visualQualityAccepted=false` remain explicit. Real Iris execution is pending at this CPU freeze.
