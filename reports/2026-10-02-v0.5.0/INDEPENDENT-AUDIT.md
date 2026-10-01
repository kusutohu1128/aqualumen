# Independent v0.5 lower-resolution quality-run audit

CPU/read-only Codex audit; final saved-data recheck at **2026-10-01 20:48:19 UTC**.
The only file written for this task is this document. No shader, raw capture,
validator, game configuration or world was changed; no GPU job, Minecraft
launch, runtime control, credential read, private-log read or process-argument
inspection was performed.

**Result: the saved 16-scene, 1600×900 quality-observation dataset is internally
consistent. This is not acceptance of the 2560×1440 benchmark contract, a fresh
measurement, a visual-quality score, or completion of the full realism goal.**

## Explicit resolution boundary

[real-view/run.json](real-view/run.json) and every scene declare both window and
framebuffer resolution 1600×900. All sixteen PNGs have that exact resolution.
The public `tools/report.py::load_run` deliberately requires 2560×1440; an
unmodified read-only invocation rejects this dataset with:

`Expected screenshot resolution must be exactly 2560x1440`

That expected rejection is preserved. Neither metadata nor the validator was
modified to manufacture a 1440p pass. The audit reused the public bounded PNG
checker with its supported 1600×900 argument, public upward-eye validation, and
public metric helper, alongside separate JSON/CSV checks and independent
integer-nanosecond metric calculations. `tools/report.py` SHA-256 at inspection:

`716e7dbbb58c736ad076f317d214f23ba542bc0e91b1b480865eb1d37201b31c`

## Dataset, identity and evidence integrity

[run.json](real-view/run.json) records run `water-v0.5-real-view`, Minecraft
1.21.1, Iris 1.8.8, Sodium 0.6.9, Java 21.0.7 and an NVIDIA RTX 3080 Ti renderer.
Settings are 12 render / 6 simulation chunks, VSync off, recorded frame-limit
value 260, default pack options, and 5 seconds warmup plus 5 seconds requested
sampling per scene. These are recorded test settings, not ordinary-handoff
settings.

- The scenario set is exactly sixteen unique scenes, with exactly matching
  sixteen scene JSONs, sixteen CSVs and sixteen PNGs; no abort record is present.
- Every scene matches its filename, run ID, pack name/SHA, exact world UUID,
  resolution and framebuffer size. Every scene records active shaders with no
  Iris fallback.
- The pack is `Aqualumen-0.5.0.zip`, SHA-256
  `88ff19eed363ff3d25287b3873ed7c0ac7b2ca654074e0365d510fedd07c859d`.
  The independently hashed `dist` archive agrees with run/expected/scene SHAs.
- The world is the approved disposable `AqualumenNaturalV2`, seed 308060,
  UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`, natural vanilla noise generation.
- Every PNG passes bounded signature, chunk-order/CRC, exact IHDR dimensions,
  RGB/RGBA format, complete zlib stream, scanline-filter and IEND/trailing-data
  checks. This verifies image-file integrity, not appearance.
- [complete.json](real-view/complete.json) matches the run/scenario set and
  reports `status:complete` and `fixture_cleanup_complete:true`. The cleanup
  flag is a completion record, not an independent persisted block/entity audit.

The final reread preserves these evidence hashes:

| File | SHA-256 |
|---|---|
| `real-view/run.json` | `4c0fd30f4b2654267d6e37be7b3b5dfa64fd373029f08a517657167b77aab241` |
| `real-view/complete.json` | `879cac5f10c02dd2041486f3bfa5f714cc12a2a5943492dc9ed2498e1995c22b` |

## Rendered poses, eyes, dimensions and contacts

All scene records contain camera locking and `camera_follows_local_player:true`;
actual camera angles equal actual player angles. The eleven ordinary fixed
poses, plus three strict upward-underwater poses, match the requested test
locations and views within the 0.05 m / 0.05 degree checks. The glass-layer
player position is intentionally 12 m behind the ocean site's reference Z, not
a failed fixed-site match.

The moving-view camera yaw is 14.990345 degrees versus expected 15.019726
(difference -0.029381 degrees), with correct pitch and stationary ocean
position. The boat is a moving, mounted-player scene rather than a fixed
position control: yaw/pitch are 0/10, the camera follows the local player, and
the recorded driver is scripted server-command translation at 6 m/s and 20 Hz.
That validates recorded contact input, not natural player-controlled rowing.

All three upward cases pass the unchanged public eye validator, including
first-person camera/eye agreement, actual WATER submersion, frozen client/server
time 6000, no terrain placement, and matching nested/top-level measured poses:

| Scene | Requested eye depth | Actual eye depth | Camera/eye separation |
|---|---:|---:|---:|
| underwater-up-near | 0.50 m | 0.499889308 m | 0.0000001192 m |
| underwater-up-deep | 3.25 m | 3.249889308 m | 0.0000001192 m |
| underwater-up-tilt | 0.50 m | 0.499889308 m | 0.0000001192 m |

Nether and End use their expected dimensions, positions and orientations; the
physics bridge is inactive there with dimension -1 and 1 respectively. All
overworld scenes record active bridge dimension 0. Each scene's six exported
physics samples agree with their embedded raw status and with scene contact
maxima; final status agrees with `*-physics.json`. The bridge is version 0.2.0,
512 resolution, 64 m span, `linear-wave-height` solver. Boat maximum contact
count is 1 and maximum force is 8.0. Coast has two observed contacts and maximum
force 2.1906, so it is not a zero-contact reference. No simulation was rerun.

## Raw-interval recomputation

All **24,701** CSV intervals are finite/positive, have contiguous zero-based
frame indices, and have integer `ns` values agreeing with exported `ms` within
`1e-8` ms. Frame counts and recorded duration agree with the CSVs; the maximum
duration discrepancy is `8.89e-16` seconds. Actual sampling windows are at least
5 seconds and are not truncated. One discarded start boundary accounts for
the recorded-interval duration being slightly shorter than the sampling window.

Mean FPS, slowest-ceiling-1% reciprocal mean, nearest-rank P99, worst interval,
minimum instantaneous reciprocal and over-budget counts were recalculated
directly from integer nanoseconds. Every exported statistic agrees; maximum
absolute numeric difference is `2.85e-14`. The public helper agrees as well.
Every scene records `window_focused:true`; this capture flag is not a continuous
focus trace throughout the measurement.

The following numbers describe the saved **1600×900** render-tail intervals
only. All scenes have zero recorded intervals over the 16.667 ms reference.

| Scene | Intervals | Mean FPS | 1% low FPS | P99 ms | Worst ms |
|---|---:|---:|---:|---:|---:|
| coast-day | 1104 | 220.8 | 147.3 | 6.330 | 7.797 |
| river-day | 1126 | 225.2 | 144.0 | 6.400 | 8.439 |
| ocean-day | 1141 | 228.3 | 152.9 | 6.109 | 7.997 |
| ocean-dusk | 1109 | 222.0 | 142.4 | 6.553 | 7.983 |
| ocean-night | 1195 | 239.1 | 161.0 | 5.982 | 6.528 |
| ocean-rain | 1037 | 207.5 | 144.1 | 6.582 | 7.781 |
| underwater | 1252 | 250.6 | 166.0 | 5.626 | 6.648 |
| underwater-up-near | 1492 | 298.6 | 175.7 | 4.927 | 7.283 |
| underwater-up-deep | 1474 | 294.9 | 182.3 | 4.983 | 6.392 |
| underwater-up-tilt | 1493 | 298.7 | 177.8 | 5.032 | 6.736 |
| moving-view | 1120 | 224.1 | 152.4 | 6.172 | 7.086 |
| boat-contact | 1127 | 225.5 | 153.2 | 6.199 | 7.895 |
| cave-water | 1295 | 259.2 | 173.0 | 5.427 | 6.503 |
| glass-layers | 1136 | 227.3 | 118.2 | 6.894 | 11.434 |
| nether-view | 4233 | 846.7 | 437.4 | 2.085 | 3.370 |
| end-view | 3367 | 673.6 | 355.0 | 2.396 | 7.038 |

The recorded `frame_limit:260` value must not be presented as proof of an
enforced 260 FPS display ceiling: several observed render-tail averages exceed
it. These observations do not establish a universal FPS floor, traversal/new
chunk performance, display presentation rate, or a pack-only improvement over
the separate 1440p v0.4 run. Resolution and focus conditions differ between
those datasets.

## Preserved baseline and remaining limits

Independent archive hashes confirm the prior v0.4 archive is unchanged:
`5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069`.
The retained v0.3.3 archive likewise remains
`ff81efa32c96f3b1c2c76c1c55fe6e32ed29f1344e67a239afeeccca980583e5`.
At the 20:40:55 UTC source/artifact check, the v0.5 ZIP's 46 shader/license
entries exactly match current candidate source bytes, with no extra/missing
entries. This does not replace or relabel the frozen v0.4 checkpoint.

This audit does not visually judge the quality-run PNGs, prove a physical lighting law from
scene captures, certify natural wakes, repeat native GPU regressions, or verify
the entire full-goal handoff. Outside the three upward controls, explicit measured
eye/submersion and client/server time/weather fields are not exported, so
additional claims about those conditions remain bounded by the available
metadata. The [full realism goal](../../docs/REALISM_GOAL.md) remains active after
this data-integrity pass.

## Ordinary runtime handoff follow-up

Separate follow-up checks at **2026-10-01 20:52:00 UTC** inspected
[ordinary-handoff.json](ordinary-handoff.json),
[user-scene/current.png](user-scene/current.png), and
[user-scene/paused.png](user-scene/paused.png), with read-only live file/stat and
`pid,ppid,comm` checks. No runtime or UI controls were issued.

- Live Java PID 2322822 has parent PID 2322731 (`prismrun`), matching the exported
  ordinary runtime evidence. The normal-account login, current pack activation,
  overworld pipeline creation and physics initialization are explicitly
  log-derived claims in the exported handoff; this auditor did not read account
  files or the private raw launch log to re-establish those claims.
- Live ordinary options pass `cmp` against the preserved pre-test snapshot,
  and both have SHA-256
  `02516270fea53cc286dceb1d5eca457f2ecc2e0ab6d2e1b15b01c4032307e5f0`.
  Values are restored to 1600×900, cap 120, pause-on-lost-focus true, VSync off,
  and render/simulation distance 12/6.
- The exact active benchmark marker is absent and there is no benchmark-named
  active `.jar`. The installed and built v0.5 archives independently have the
  expected `88ff19eed363ff3d25287b3873ed7c0ac7b2ca654074e0365d510fedd07c859d`
  SHA. Live Iris configuration selects v0.5 with shaders enabled and debug
  options disabled.
- Both ordinary-scene PNGs pass the 1600×900 integrity checker. Direct visual
  inspection confirms an in-world shoreline scene and, separately, the Japanese
  pause/game menu with the return-to-game and save-and-return-to-title controls.
  This is application-state evidence, not photorealism acceptance or a motion
  test. PNG SHAs are `1803d1198a0611669bf38d396361f4adbcb24b0531a7724409d134fcbf5d0d92`
  for current and `b2595363e38304aa21b1ac660b8894dcff237f963fcb65a0dbb55348fe4459e8`
  for paused.
- Ordinary `新規ワールド/level.dat` is now 2402 bytes with mtime
  `2026-10-02 05:48:12.023889400 +0900`, exactly corresponding to the handoff's
  post-normal-pause-save timestamp `1790887692023889400` ns. Its earlier
  pre-test timestamp is preserved in the export. A normal launch resumes normal
  saves; continued byte identity of an open user world's `level.dat` is neither
  expected nor claimed. No world contents were read or written by this audit.

The narrow point-in-time ordinary-runtime/settings handoff is therefore
supported by the exported login/pipeline evidence and the independent live
file/process/screenshot checks. It does not retroactively make this 1600×900
capture a 1440p benchmark, prove every user-world artifact unaffected, or close
the remaining cloud/shore/motion/full-realism requirements.
