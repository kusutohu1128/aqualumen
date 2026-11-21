# Interrupted GH-phase experiment: recovered checkpoint

2026-10-05 JST. This is a recovery record, not a new GPU run, visual fix,
candidate promotion, or completed goal. Existing report packets, source changes,
worlds, and independent reviewers' files were not edited. No CPU test suite,
native probe, or completed phase0 Minecraft benchmark was rerun during recovery.

## Exact stop and completed reviews

The parent session `01a0f709-5ba6-7840-b5b8-359bea995208` was read directly.
Its last completed operation at 2026-10-03 23:12:20–23:12:22 JST changed only the
selected pack/expected pack from phase0 physical to phase45 physical, then
launched Aqualumen Lab / AqualumenNaturalV2. Owned launch handle was 67000.
The parent stopped before issuing a phase45 benchmark request. A subsequent
clean exit of this handle was not recorded; the user reports closing Lab.

- `opus_review`, session `01a0f742-00c1-79d3-a440-4ca36c76ce98`, final answer
  at **23:20:05 JST**: independent saved native audit PASS; 366 comparisons and
  all masks/counts recomputed without discrepancy. Observer C0/depth passivity
  is qualified only for those fixtures. Their admission masks did not change,
  so the natural cloudy scene's dark-band cause remains unestablished.
  See [independent audit](../independent-native/README.md).
- `water_geometry_review`, session `01a0fe4f-f122-7410-9fe9-58e1204fcdad`, final
  at **23:24:12 JST**: immutable-file reader READY, six CPU regressions PASS;
  the first actual saved stage/guard pair qualified (int1, four linked stages,
  patch3). **Not** a completed four-role geometry comparison: three pairs are
  still missing. See [saved test log](../independent-stage/05-final-public-cpu-green.log)
  and [reader](../independent-stage/audit.py).

Recovery checked the independent-native SHA256SUMS: its README, audit.json and
reader all matched. This was an artifact-integrity check, not a replay of the
366 comparisons. The installed phase45 physical ZIP and repository ZIP both
hash to `d0dbf90d3470eb6faac24a5e2077ce3cb1ef1b1fc56aa8debb6942015da6187b`.

## Live configuration observed read-only

Only the existing isolated Lab was inspected:
`/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft`.

The latest game log ends at **2026-10-03 23:12:49 JST**, after the phase45 pack
loaded, V2 joined, and physics 0.3.0 initialized. There is no phase45 benchmark
completion in it. The benchmark status is `idle`, updated 23:12:32 JST, not a
current heartbeat. The only GH run directory is `ghphase-0-physical-20261003-2307`.
No benchmark request, shore request, Sun-guard request, or water-stage request
is pending. `pgrep -x java` returned exit1/no matches in the current environment.

World marker: schema2, UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`, seed308060,
generator `minecraft:noise/overworld`, Minecraft1.21.1. Selected shaders are
enabled; selected/expected pack is phase45 physical. Window override1600×900,
render12, simulation6, FOV0, maxFPS120, VSyncfalse, pauseOnLostFocusfalse.

Active JARs: benchmark0.3.9 projection guards, physics0.3.0, stage-probe0.1.0,
Sun-test0.1.0 observer-v2, Iris1.8.8+mc1.21.1, Sodium0.6.9+mc1.21.1.
Benchmark/Sun-test enable markers remain present. Normal physics0.2.0 remains
recoverably disabled. **Lab is still in TEST configuration; ordinary return
has not happened. Do not use this setup to benchmark ordinary user worlds.**

Safe copies of the observed game log and non-secret configuration are in this
new directory. No launcher/account/authentication log was copied. Snapshot SHA256:

| File | SHA256 |
| --- | --- |
| phase45-launch-runtime.log | `cfdc4512fd9d590532dc0cd1ed4b815c89a79b2455f9923c9ac6a42748abcac3` |
| iris.properties | `dbd5f1c2d01304d4784b2912ebfcbe7b0cbc6fb800ffc12bf2a8171d426a792a` |
| aqualumen-benchmark.properties | `a6af629a942b41d20c0d4c5751434d0e6c11e70d94f1fba4dc18eaa3c555984c` |
| options.txt | `6a8f5a5ee4df9dfca07262c0099122c9037041f23d467a8d13949395451e1888` |

Completed phase0 physical means: near14.930589, deep13.291815, tilt18.221077 FPS,
all1600×900, active pack, no fallback. These are **Minecraft scene timings**,
not native harness timings or 1440p measurements. The saved native renderer is
RTX3080Ti / GL4.6 NVIDIA580.173.02; the saved actual Iris context is GL3.2
NVIDIA580.173.02 with ARB tessellation support. Neither is a current GPU result.

## Intended next action, without redoing completed runs

1. Once the original Lab is writable and host GPU execution is available,
   verify no competing client and recheck exact V2 identity/installed pack.
   Restart the existing phase45 physical configuration. Use a fresh run ID;
   do not reuse the phase0 run ID or overwrite any report artifacts.
2. Run `underwater-up-near underwater-up-deep underwater-up-tilt`, warmup5s,
   sample5s, in that order, with no observation requests during timing.
   After completion, capture separate guard and stage observations and retain
   their UUIDs/times/scopes. Copy results into new paths before the next launch.
3. Obtain phase0 diagnostic and phase45 diagnostic observations with the same
   scenes/poses/fixed phase. After measurement hold the near view and use the
   original ordered16 texels. Preserve the minimum4 Sun-application gate;
   failed/no-application observations are evidence, not a waived PASS.
4. Use `tools/water_gh_phase_runtime.py RAW PACK GUARD_RAW` for new diagnostic
   records and the fixed independent-stage reader for the completed four
   role pairs. Compare actual Iris-rewritten VS/TCS/TES identities across roles,
   not archive-expanded source hashes. Keep each observer event separate from
   a draw/fragment/freshness proof.
5. Inspect the diagnostic atlas against the persistent arcs/rim: separate
   full/base admission changes from fixed-admission color changes, original
   flags/grazing handoff, and mean receiver/SSR handoff. Phase rotation is the
   single optical variable; do not combine density/settings tuning or promote
   phase45 without evidence that addresses the actual natural-scene defect.
6. After clean TEST exit, disable instrumentation/opt-in markers and restore
   ordinary0.6 / physics0.2 configuration from the existing private cache
   `/home/kusutohu/.cache/aqualumen-gh-phase.BN6hPp`. Verify a fresh ordinary
   paused image. The private whole-save copy is **comparison only: never
   restore it over the live save**.

## Current execution boundary

This resumed session permits writes only under the repository and /tmp, with
approval disabled. The existing Lab and private cache are outside those roots;
launching/configuring Minecraft would write there. `/dev/nvidia0` and
`/dev/nvidiactl` are also absent in the current environment. Therefore no
launcher, benchmark start, live config modification, GPU replay, normal restore,
world replacement, new external model call, commit, or push was attempted.
Do not route through another process or clone the instance to bypass this
boundary. Continue at **phase45 physical**, when the original Lab/host runtime
is legitimately available. The source implementation and full realism goal
remain unaccepted; the black-band cause is unresolved.
