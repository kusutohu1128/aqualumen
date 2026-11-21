# Rain-eave native fixture — progress for the parent

- 04:39–04:41 `build-r1` complete: covered stone patio over the open ocean (biome `minecraft:ocean`,
  checked from the region file and by a server `location_check` at all 14 receivers) at world
  x 399..413, y 63..70, z -441..-427 in a private exact-UUID/seed V2 clone. Saved geometry re-read
  from the clone's region files after exit: all 1800 reserved cells exact. Snapshot kept read-only at
  `/tmp/aql-rain-fixture-build-b56batsu/minecraft/saves/AqualumenNaturalV2`.
- Saved skylight in front of the receivers: exposed 15, sheltered near 13, sheltered far 11 (so the
  sheltered strip is *not* dark to a skylight-based model). Server `can_see_sky`: exposed 1, sheltered 0.
- Your update read: using `build/Aqualumen-1.7.0-rain-rc2.zip` (sha256 5b27ec8f…4376), runs `rc2-r*`.
  rc1 is not run. Half-lives found in rc2: `const float wetnessHalflife = 60.0`, `drynessHalflife = 240.0`
  (`shaders/lib/rain_surface.glsl`), recorded per run.
- Campaign unit `aql-rain-fixture-campaign2` (systemd --user): waits for `/tmp/aql-render21-1000.lock`
  (currently held by `material/capture.py`), then `base-r1` (1.6.0), then `rc2-r1`, then `measure.py`.
- Status/timing: `status.json`. No help needed right now.

## 04:57 update
- `base-r1` (1.6.0, sha 0b1843fd…) complete on RTX 3080 Ti, no DRIFT/FAIL, source and snapshot unchanged.
  1.6.0 shows only rain streaks: post-rain and final-dry patch luminance equals dry exactly (ratio 1.00000);
  late-rain exposed/sheltered stone ratio changes −2.7 % (pose A) from streaks in front of the patches only.
- Read your rc3 update. `aql-rain-fixture-final-patio` (your unit, my scripts with rc3 prefix) will run `rc3-r1`;
  I will not rerun the baseline and will only measure/compose after rc3-r1 completes.
- Model in measure.py: rc3 `wetnessHalflife 60` → 6 s up; no dryness directive → Iris default 200 → 20 s down.
