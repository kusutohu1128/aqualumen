# Normal configuration return — filesystem audit

Status: PASS within the read-only filesystem scope below. This is a later checkpoint than the initial normal-client-stopped checkpoint in [LIFECYCLE.md](LIFECYCLE.md).

## Selected normal configuration

The current Iris configuration selects `Aqualumen-0.6.0.zip`, with shaders enabled. Its installed SHA-256 is:

`6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`

Only these three immediate `mods/*.jar` files are enabled by filename; their embedded Fabric metadata was also checked:

| Mod | Version | SHA-256 |
| --- | --- | --- |
| Aqualumen physics | 0.2.0 | `1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e` |
| Iris | 1.8.8+mc1.21.1 | `b5ad39a6cb113ca0a1765f06689f9f4b29ccd0c81247de90b06c42f5da1092f5` |
| Sodium | 0.6.9+mc1.21.1 | `411c4c03167066f0e2e61ba17793b4be13ddd73de5b677c6d402f1d8f4262ac2` |

No benchmark, stage-observer, Sun-test or physics 0.3 top-level JAR is enabled. Suffixed disabled/closed archives remain; this audit does not claim they were deleted or independently enumerate live loaded Mods.

## Configuration comparison

Compared with the private prelaunch copies:

| File | Result | Current SHA-256 |
| --- | --- | --- |
| `options.txt` | Exact byte equality | `02516270fea53cc286dceb1d5eca457f2ecc2e0ab6d2e1b15b01c4032307e5f0` |
| `config/aqualumen-benchmark.properties` | Exact byte equality | `45a4c9b0269ec47b3a72fa73647e92702b6012be10f273a60d37f69c9ca148d1` |
| `config/iris.properties` | All noncomment lines and parsed values equal; comment-only byte difference | `bb3d72ef62e252a4503c0badd87bbd4859876e981ff93e559ee102e1e68816d7` |

The original Iris file SHA-256 was `6ea051391c010bda752e44b7063bded80a77e5329539738383413553a874a768`. Whole-file byte equality is therefore **not** claimed for Iris.

Normal options retain 1600×900 override dimensions, a 120 FPS cap, VSync off, render/simulation distances 12/6 and pause-on-focus-loss. The dormant benchmark configuration retains its original 2560×1440 request; it does not establish the current normal framebuffer or an active benchmark.

## TEST entry points

The following exact active basenames are absent, including symlinks:

- `config/aqualumen-benchmark.enabled`
- `config/aqualumen-sun-test.enabled`
- `config/aqualumen-shore-observe.properties`
- `config/aqualumen-water-stage-observe.properties`
- `config/aqualumen-sun-guard-observe.properties`
- `config/aqualumen-bathymetry-observe.properties`
- `config/aqualumen-solar-cache-observe.properties`
- `aqualumen-benchmark/request.properties` and `command.properties`
- `aqualumen-benchmark/control/request.properties` and `command.properties`

The only unsuffixed `aqualumen-*.properties`/`.enabled` configuration entry is the unchanged dormant benchmark properties file. There are no `*.properties` files within the benchmark control directory's first two levels. Archived suffixed requests remain inert under the source's exact filename contracts.

## Root-owned live handoff and limits

Root reports the normal client relaunched in owned session 53001 and visually confirmed paused at 20:48:38. This independent audit checked the saved [ordinary-return-paused.png](ordinary-return-paused.png) with the public strict PNG reader: integrity and 1600×900 dimensions passed; SHA-256 is `e93f5c8a174f6b0fc3422f4c57dd361bcce9eb29dfee6c501744d4130ae1ddd5`.

The live UI confirmation is attributed to Root, not a second client/UI inspection by this auditor. This audit makes no save-after-launch world identity claim, no current FPS claim, no candidate promotion and no natural-water visual acceptance claim. Authentication logs, private backup paths and Java command lines were not read or published for this audit. No game, configuration, source or runtime file was changed; this new report is the sole write.
