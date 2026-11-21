# Forest torch beauty comparison — private scratch kit (no game launched, no render produced)

Everything here is read-only analytics of the exact TEST save (`AqualumenNaturalV2`, UUID
`b22dbccb-2970-41e6-847f-f183b1ec923d`, seed 308060) plus a **private** benchmark JAR built from a pinned snapshot.
Nothing under `tools/`, `shaders/`, saves, configs or the Minecraft instance was modified or installed.

## Site (natural, no platform)

| item | value |
|---|---|
| tree | genuinely generated **birch**, trunk base `(209,64,360)` on generator dirt, 7 logs, crown of `persistent=false` leaves |
| camera feet / eye | `(208.5, 64.0, 355.5)` / eye `y=65.62` (spectator tp, 5.10 m from the trunk base), yaw `12.7`, pitch `-2.0` (≈ horizon, faces +Z; sun on the right) |
| torch slot | `(207,64,359)`: exact AIR, on natural `grass_block (207,63,359)`, AIR above; 4.24 m from camera, 2.24 m from the trunk axis |
| frozen time | **9800** for off/warm/soul (late afternoon band 9200–10200; sun elevation 44.7°, toward −X) |
| optional night | **15500** (same pose) |
| verified existing cells | 49 read-only: trunk logs, trunk-base dirt, torch/camera support, 7 near + 26 distant `persistent=false` leaves, 6 distant trunks (all 133 crown leaves near the trunk are `persistent=false`) |
| reserved exact-AIR cells | 5: torch slot, cell above it, camera feet/eye/head cells |

Analytic composition at 96×54 rays from the exact eye (`forest-site.json`): ground 39.6 %, target trunk 7.7 %, other trunks 10.3 %,
foliage 6–16 m 10.7 % and >16 m 7.5 % (near leaves <6 m 8.3 %), sky 13.1 %, water 2.5 %, outside grid 0.2 %; 554 rays cross grass/plants.
Torch flame is voxel-clear from the eye and projects to NDC (0.019, −0.389) ≈ pixel (1304, 1000) at 2560×1440 / FOV 70; trunk base sits at NDC (−0.36, −0.46).
Java `LocalLightFixture.project` reproduces the Python pixel (ForestSiteTest). The 5.1 m distance and framing are a heuristic search result, not a
visual judgement — look at the PNG.

Solar / light notes (analytical lab geometry, **not measurements**): the camera-facing (−Z) bark face is grazing to the sun (sun has no Z component) and
the voxel sun ray is unblocked for all samples; flood-fill block light: torch 14 → trunk-face air cell 11, camera cell 8; soul torch 10 → 7 / 4.

## Scene key → real scene (private JAR only)

| scene key | variant | block placed in slot | time |
|---|---|---|---|
| `ground-noon` | **off** | none | 9800 |
| `ground-evening` | **warm** | `minecraft:torch` | 9800 |
| `ground-low-sun` | **soul** | `minecraft:soul_torch` | 9800 |
| `air-shadow-backlit` (optional) | night off | none | 15500 |
| `air-sunlit-front` (optional) | night warm | `minecraft:torch` | 15500 |
| `air-backlit-open` (optional) | night soul | `minecraft:soul_torch` | 15500 |

`ground-sun-motion`, `ground-camera-motion`, `opaque-*`, `lamp-*`, ocean/underwater keys keep their original behaviour in this JAR.
**Do not use this JAR to reproduce the original ground-shadow or air-shadow scenes** (those six keys are re-purposed). Forest scenes must run alone
(no clip/motion capture) and only in the exact UUID + seed world.

## Safety model implemented in the patch

* `OcclusionFixture.parse` returns the forest plan for the six keys; the existing opt-in config, request, `guard()`, exact-UUID `fixtureScope()`, journal
  (`opaque-fixture-journal.json`, written before placement) and cleanup path are reused. The patch adds a seed-308060 check.
* Before placement: every reserved cell must be AIR, all 49 existing cells must match id + `persistent=false`/`axis=y` (server thread, strict).
* Pre-sample (server thread): torch state exact for the variant, reserved AIR, existing cells again; capture refuses without that evidence.
* Capture: first-person eye/camera/player within 0.05 m of the site, rotation within 0.05°, frozen time equality, torch/bark pixel projection and
  `forest_light` evidence in `<scene>.json`.
* Cleanup: slot restored to AIR, then post-cleanup validation of every existing cell; any mismatch keeps the journal (blocks further runs until reviewed).
* Only one block is ever mutated; no terrain is replaced; saved chunks within 13 chunks of the camera are all `minecraft:full` (729/729), so no new terrain is generated.

## Build / audit commands

```
python3 -I reports/2026-11-20-local-light/forest-tools/audit_forest_site.py      # read-only; run with the game closed, before and after
bash reports/2026-11-20-local-light/forest-tools/build-forest-jar.sh              # refuses to overwrite; already built once
# JAR: build/aqualumen-benchmark-forest-light.jar  (mod id aqualumen_benchmark, version 0.3.9-forest-light)
```

Regenerate from scratch: `snapshot.py` (refuses to overwrite) → `scan_trees.py` / `find_site.py` / `site_report.py` → `apply_forest_patch.py` → build.
`forest-light.patch` is the diff of `jar-src-orig/` (pinned snapshot, hashes in `snapshot-original-sha256.txt`) vs `jar-src/`.

## Run (Codex owns the runtime)

The JAR uses the same mod id as the regular benchmark JAR: install it **instead of** (not next to) the regular one in the `Aqualumen Lab` instance only.
Equivalent request through the repo control tool (config opt-in files already required by the mod):

```
python3 tools/benchmark-control.py start --scenes ground-noon ground-evening ground-low-sun --warmup 20 --sample 10
python3 tools/benchmark-control.py start --scenes air-shadow-backlit air-sunlit-front air-backlit-open --warmup 20 --sample 10   # optional night
```

`/tmp/aqualumen-light-game.py` could not be read by this task (no read permission), so the exact runner invocation is Codex's to adapt: it only has to
send `scenarios=ground-noon,ground-evening,ground-low-sun` (screenshots: `runs/<id>/<scene>.png` and `screenshots/aqualumen-<id>-<scene>.png`).
Use ≥15 s warmup so block light and meshes settle. After the run: `audit_forest_site.py` must report `ok: true`.

## Limits and honesty

* No game was run: block-light/sun values are analytical models; visual quality of the composition is unproven until the screenshots exist.
* Sequential screenshots: clouds, exposure and foliage wind are not pixel-locked; torch visibility vs shader behaviour is exactly what the run measures.
* The pinned snapshot is the working tree at copy time. `tools/.../Recorder.java` has since gained `localCameraProjection` (Iris captured matrices,
  lamp scenes only) from another agent; it is not in this JAR. Forest evidence uses pinhole projection with options FOV (recorded) instead.
* The existing suites `OcclusionFixtureTest`/`AirShadowFixtureTest` are intentionally not run (they assert the original meaning of the six aliased keys);
  `ForestSiteTest`, `LocalLightFixtureTest`, `ScreenshotCompletionTest`, `NativeMotionCaptureTest`, `UnderwaterSceneTest` pass in the build.
