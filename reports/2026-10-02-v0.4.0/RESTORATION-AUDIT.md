# v0.4 ordinary-settings restoration audit

Read-only Codex audit at **2026-10-01 20:20:40 UTC** (2026-10-02 05:20:40 JST).
The sole edit made for this audit is this document. No Minecraft launch, GPU
work, configuration/world mutation, account-file read, process-argument read or
private-log read was performed.

**Result:** the recorded ordinary settings and disabled instrumentation are
independently confirmed on disk. **A fresh ordinary-account runtime relaunch
remains unverified.** This is a restoration checkpoint, not a completed runtime
handoff or completion of the [full realism goal](../../docs/REALISM_GOAL.md).

## Artifact boundary

The frozen v0.4 checkpoint is commit
`6dd4e5aa5d5bc62d523b76990b741c133c07579d`. Current working shader sources may
already contain subsequent v0.5 work; this audit does not equate those sources
with the installed v0.4 archive.

Both `dist/Aqualumen-0.4.0.zip` and the installed Lab
`minecraft/shaderpacks/Aqualumen-0.4.0.zip` independently hash to:

`5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069`

This matches [after/run.json](after/run.json), every candidate scene metadata
record, [temporal-run/run.json](temporal-run/run.json), and
[ordinary-settings-checkpoint.json](ordinary-settings-checkpoint.json).
Live Iris settings select `Aqualumen-0.4.0.zip`, enable shaders, and disable
debug options. The archive identity is confirmed; a selected configuration
alone is not a new runtime shader-activation test.

## Independently checked restoration

The instance is
`/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab`;
all live file checks below are confined to that instance.

| Item | Evidence and result |
|---|---|
| Ordinary game options | `build/snapshots/v0.4.0/options.txt` and live `minecraft/options.txt` pass `cmp` and both hash to `02516270fea53cc286dceb1d5eca457f2ecc2e0ab6d2e1b15b01c4032307e5f0`. |
| Restored option values | Width/height 1600×900, `maxFps:120`, `pauseOnLostFocus:true`, render/simulation distance 12/6, VSync off, fullscreen off. These are restored settings, not newly measured frame timings. |
| Instance settings | Snapshot/current `instance.cfg` are identical after excluding only `lastLaunchTime`, `lastTimePlayed`, `totalTimePlayed`, and `notes`. The complete changed-key list is exactly those four keys; no other setting differs. Play counters and updated release notes were intentionally retained. |
| Benchmark loader | No benchmark-named file ending in `.jar` is present in `minecraft/mods`. `aqualumen-benchmark-0.3.3.jar.0.4-release-disabled` exists, so removal from the active loader set is recoverable. The ordinary physics bridge remains installed. |
| Benchmark opt-in | The exact active marker `minecraft/config/aqualumen-benchmark.enabled` is absent. `aqualumen-benchmark.enabled.0.4-release-disabled` exists. Older disabled copies do not restore the active marker. |
| Stopped client observation | A read-only `pid,comm` inventory found no process named `java` or `prismlauncher` (case-insensitive). No argument strings or private launch logs were inspected. This is a point-in-time observation, not an ongoing process monitor. |
| Ordinary-world metadata | `minecraft/saves/新規ワールド/level.dat` was only inspected with `stat`: 2407 bytes, mtime `2026-10-02 03:31:47.505105917 +0900`, before the isolated v0.4 runs. Its contents and other ordinary-world files were not inspected. |

At the initial 20:20:40 UTC audit, the exported ordinary-world mtime was
`1790879507505106000` ns, 83 ns above the directly observed filesystem value
`1790879507505105917` ns; the fixture-region export was likewise rounded by
86 ns. The root agent identified a JavaScript JSON parse/re-emit of integers
above `2^53` as the metadata precision loss, not a world write, and corrected
the records with literal patches at 20:22:26 UTC. A subsequent literal-text
reread confirms the corrected ordinary-world value
`1790879507505105917` ns and post-motion region value
`1790884599576665686` ns exactly match this audit's filesystem observations.
This paragraph preserves the initial discrepancy and its correction; all live
restoration findings remain the historical 20:20:40 UTC checkpoint, not a claim
about the later re-enabled instrumentation for the next isolated v0.5 test.

## What fixture cleanup proves

[fixture-after-motion-stop.json](fixture-after-motion-stop.json) records a
read-only persisted Anvil palette/block-state audit of six temporary wall and
target plots in the exact UUID-guarded disposable world. It reports 390 unique
cells, all `minecraft:air`, no non-air cells, no pending fixture journal, and
`cleanup_pass:true`. It explicitly records no world writes or control requests.

The current `AqualumenNaturalV2/region/r.0.-1.mca` is 9,388,808 bytes and
independently hashes to
`57e6d585d40513ed72848dac0417fcb5f73677ca7e6a0bba6beecd531a66541e`, exactly
matching that audit. Thus the saved region bytes containing the audited cells
have not changed since that exported check. This independent pass did not
repeat the Anvil decoding; its block-state conclusion is supported by the
exported parser result plus the matching current region hash.

[before/complete.json](before/complete.json),
[after/complete.json](after/complete.json), and
[temporal-run/complete.json](temporal-run/complete.json) each match their run
and scenario set and report `fixture_cleanup_complete:true`. These completion
flags alone are not independent persisted block/entity inspections. Neither
they nor the 390-cell AIR audit establish blanket world integrity, absence of
every temporary entity, restoration of every possible fixture location, or a
successful ordinary-world relaunch. The ordinary `level.dat` mtime is similarly
bounded metadata evidence, not a checksum audit of the whole ordinary world.

## Temporal evidence is separate from ordinary handoff

[temporal-run/run.json](temporal-run/run.json) and its four scene records use
the same v0.4 pack SHA and guarded world UUID, active/non-fallback shaders,
1600×900 framebuffer/window, and a completed four-scenario run. All four
captures record `window_focused:true`; rendered camera angles follow the local
player. This was still an instrumented test run at frame limit 260, not a fresh
ordinary-account run with the restored cap of 120.

The three MP4 files named by
[temporal-video-audit.json](temporal-video-audit.json) were independently
hashed and match that exported audit. Its recorded 20-second/1200-frame clip
properties, decoded hashes and timestamps describe saved recording integrity;
this restoration audit does not re-decode or visually score those clips and
does not infer native Minecraft FPS from a 60 FPS video container. Those
1600×900 observations must not replace the separate saved 2560×1440 performance
baseline or be called fresh measurements.

## Remaining handoff condition

`fresh_ordinary_runtime_relaunch_verified:false` remains explicit in the
checkpoint. A normal, non-benchmark account launch must still confirm the
selected v0.4 pack is actually active without fallback, the restored ordinary
settings are used, and ordinary play remains usable with development controls
disabled. This audit does not perform or pre-approve that verification.
Cloud/sunlight coherence and the remaining full realism requirements are also
still active; restoring settings does not complete the rendering goal.
