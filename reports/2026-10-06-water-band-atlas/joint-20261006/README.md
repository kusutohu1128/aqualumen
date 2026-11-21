# Same-quad atlas output and selected GH admission comparison

2026-10-06 JST. Concrete TEST observation progress, **not an optical fix or full
realism acceptance**. Current tracking work and all old evidence are preserved.
The previous permission-explanation turn was no progress; this continuation
revalidated live owned handle93848 and obtained the missing phase45 records.
The earlier portion of this diagnostic cycle also implemented the new observer
and obtained phase0 records. Completed phase0/45 **physical** runs and the old
four-role geometry comparison were not repeated. The two new tilt runs below
are diagnostic-only recordings, not replacement physical benchmarks.

## What was implemented and actually observed

- `tools/atlas-joint-probe`: version0.1.3 captures pre-quad raw C9–C15 and five
  C0 taps at each selected source point, actual FINAL source/view/uniforms, then
  the corresponding eight display-tile pixels after the **same** FINAL quad.
  Exact disposable V2 UUID/seed/world/pack guards exclude ordinary-world GL.
- `tools/water_atlas_joint_runtime.py`: pins actual linked FINAL source, checks
  integer atlas mapping, actual LINEAR/CLAMP32F inputs, linear/non-sRGB RGBA8
  output, all caller restoration and the output framebuffer's own read-buffer
  restoration. RGB2/255 is an **encoded RGBA8 correspondence** bound, not an
  optical energy/radiance tolerance.
- Native output seam fixture (`native-output-state.json`, exit0) executes on
  RTX3080Ti / GL4.6 NVIDIA580.173.02. It reproduces the target-FBO read-buffer
  leak negative and verifies the correction,11 caller fields, correct routing,
  passive whole-output/subsequent-draw bytes and two repeats. This is not an
  Iris test or water-quality result. Seven synthetic Java boundary cases and
  eight CPU auditor regressions passed during the earlier observer build;
  actual Minecraft records below are the distinct real-runtime qualification.
- Actual Minecraft/Iris GL is **3.2 NVIDIA580.173.02**, not the native4.6
  context. Both phase clients load the exact aligned-v2 TEST packs without
  fallback. Actual before/after snapshots and encoded outputs are available.
  Neither shader-local address reads nor individual water producer invocations
  are directly observed; no such proof is inferred from these snapshots.

Sources, raw packets, audits and failures are retained. The v0.1.3 source/JAR
are frozen separately from failed v0.1.2; no old sealed helper was edited.

## Separate gates and packets

| Packet | Phase0 | Phase45 |
| --- | --- | --- |
| Original ordered16 points, Sun applied | 11/16 | 11/16 |
| Alignment16 selected points,8 tiles each | PASS | PASS |
| Alignment maximum encodedRGB error | 0.00210014235 | 0.00214420760 |
| Separate band4 points,8 tiles each | PASS | PASS |
| Band maximum encodedRGB error | 0.00199686880 | 0.00196078420 |

Original16 and the unchanged minimum4 application gate remain mandatory.
The four band points are **never padded to16 or substituted for that gate**.
Each band audit requires a separately passed alignment report of the same pack.
`phase*-joint-*-audit.json` were produced by the actual CLI with exit0.
`compare-selected.py` revalidates the packets before descriptive comparison;
`selected-comparison.json` is its exit0 result.

Phase0 pack SHA256:
`90c7d9dc1d98dfd45ff050f2f08e0bd516b756a1109dd19d738d969723da341d`.
Phase45 pack SHA256:
`b8bd19dff8c61b83311168e10eaa5704d2271ac805890404d4781cc316608069`.
Actual atlas-joint0.1.3 JAR SHA256:
`88d14a3f71adc135cab06b9ada82a19cda3ba0a328bfb75da2ca5bd439e847e8`.
Actual atlas-final0.1.3 JAR SHA256:
`6ce3747695e5d5e973f2e5c8aa9f1b0414a05abd95ab26ce203a5ad7f54091f0`.

## New selected finding, not whole-band causality

Four source pixels: `(1114,181)`, `(1114,169)`, `(1114,155)`, `(1114,151)`.
Corresponding tile-local pixels: `(278,90/84/77/75)`; top-row PNG y359/365/372/374.
Actual linked VS/TCS/TES hashes agree between the two phases. All four selected
TES marker values and outer flags/grazing/mean-receiver/SSR lanes agree bitwise.
FINAL transport uniforms agree; both packs freeze wave/sky time to120seconds.
The **only changed shader member** is the pre-Cholesky lattice phase in
`lib/water_residual.glsl`; Sun48 helper and geometry shader files are unchanged.
Other changed ZIP members are parent archives/expanded attestations/manifests.

At `(1114,155)`:

| Observation | Phase0 | Phase45 |
| --- | --- | --- |
| Legacy full valid/applied | 1/1 | 0/0 |
| Legacy base valid/applied | 1/1 | 0/0 |
| Minimum facing | 0.437527329 | 0.458920360 |
| Receiver violation count | 0 | 0 |
| Sun requested/applied | 1/1 | 1/0 |
| Sun certificate calls | 48 | 0 |
| Sun rejected lane | 0 | 1 |
| C15 water red | 0.0218732674 | 0.0064622811 |
| Displayed C0 red | 0.156862751 | 0.0980392173 |

The legacy all-or-nothing validity state is phase-sensitive at this selected
dark region. Sun rejection here is **before the48-loop**, not a recorded
inverse-Snell node failure: all four Sun reason lanes remain0. In admitted
selected points, all48 certificate outcomes are absent/zero, with0 supported
and0 unknown. This does not show a positive native-Sun contribution or justify
a Sun gain/blur change. The other three selected pixels remain admitted in
both phases but also change color, so fixed-admission quadrature/source response
remains a separate issue.

This narrows the next seam. It does not identify the exact compound legacy
predicate, prove full-frame input equality, classify every visible arc, or
accept the physical meaning of either phase. n/v/covariance and first failed
node directions were not captured. Positive recorded minimum facing and zero
receiver violations are useful exclusions at this point, not a complete
independent optical reconstruction. The original PNGs were both inspected;
fine dark arcs and the distorted/polygonal water rim persist. **No optical,
natural/temporal, energy, shipping or full-goal acceptance.**

## Timing, kept distinct

Two diagnostic-only tilt runs,1600×900, warmup5s/sample5s,90 intervals each:
`joint-0-tilt-20261006-1020` mean18.072449FPS / P99 57.314303ms;
`joint-45-tilt-20261006-1024` mean18.067888FPS / P99 58.749002ms.
Raw intervals, actual poses/eye metadata and images are retained under the
two `phase*-tilt-run/` folders. Observation requests were issued after sampling
and shader reload. These are not1440p, ordinary-pack timings, an isolated GPU
speed comparison, temporal acceptance or an FPS guarantee. Old60FPS floor
remains relaxed; this slow experimental workload is reported honestly.

## Retained failures and bounded corrections

1. Initial installation precondition failed because the physics0.3 build JAR
   path did not exist. A following launch with only normal physics0.2/Iris/
   Sodium happened, was saved/closed, and is **not** an accepted TEST run.
   `failed-install-precondition-client.log` is retained. Corrected installation
   used the existing recoverably disabled physics0.3 candidate with checked SHA.
2. Real loader failure of atlas-joint0.1.2: helper classes shared the mixin
   package, producing `IllegalClassLoadError`. Mixin was moved to `.mixin`,
   helpers kept outside it, version0.1.3 built; actual Minecraft then loads
   and supplies available snapshots. `mixin-package-failure-game.log` and
   v0.1.2 source are retained. Crash is not a normal Minecraft exit0. The saved
   console window was later closed with WM_DELETE_WINDOW, not force-killed.
3. The first descriptive comparator incorrectly expected **minimum facing**
   to match between rotated node sets. Its assertion failed; the empty output
   is retained as `selected-comparison-failed1-empty.json`. That assumption
   was removed, not a physical gate loosened: the field is compared/described
   and stays positive. TES/outer/uniform equality and all correspondence gates
   remain checked; the final report does not claim facing equality.

## Safe ordinary restoration and actual handoff

Fresh baseline is `prelaunch.json`; private cache
`/home/kusutohu/.cache/aqualumen-atlas-joint-host-_1slmtnf`.
Do not replace it with an older backup. Launcher logs remain private and are
not archived: they can contain authentication material.

Owned phase0 client62761 and phase45 client93848 each save all dimensions and
exit0 normally after exact-UUID quit requests, with Java absent before changes.
Six TEST JARs and six active controls were recoverably renamed; nine possible
instrumentation entry points are absent. Normal physics0.2/Iris/Sodium active
JAR hashes match baseline. Original three config files were byte-restored.
All41 ordinary saved files matched the fresh prelaunch baseline **before**
reopening; no save backup was restored, no ordinary camera/time/terrain was
automated. `restoration-before-relaunch.json` documents those checks.

Normal0.6/physics0.2 is freshly launched into `新規ワールド`, actual rendered
view and pause image inspected. Server records save/pause10:33:58JST;
`ordinary-paused.png` is10:34:03. Owned handle23157 is left live and paused.
`ordinary-handoff.json` records actual mod/renderer/pack evidence, not the stale
physics0.3 status file. Options/benchmark remain byte-equal after relaunch;
Iris regenerates only its timestamp comment, checked via property equality.
No native GL runs after this handoff.

**Separate pre-existing limitation:** OpenAL device initialization fails and
Minecraft disables sound/music. The same error is in the earlier ordinary
launch and TEST log. Audio stack/configuration was not changed and an audio
fix is not claimed. Shader rendering and normal pack restoration are verified.

Frozen old manifests remain valid: prior host390 files and recovery114 files
checked again from repository root. Original tracked diffSHA is unchanged:
`ee4e019473a0468d187e9d3567ec1b1e30f4c6a5dc6b0526c494c3dcbfdd52c5`.
No commit, push, external Claude invocation or memory write was made.
The full realism objective remains **active and unachieved**; see [RESUME.md](RESUME.md).
