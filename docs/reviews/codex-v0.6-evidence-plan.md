# v0.6 candidate evidence export and independent-audit plan

Initial read-only inspection checkpoint: 2026-10-01 22:21–22:27 UTC (2026-10-02 07:21–07:27 JST). Only this plan was written by this reviewer in that initial task. Root owns exports, release/version changes, builds, shipping, and runtime controls. No GPU/game/configuration action or new measurement was performed by this reviewer. The working tree was evolving; the original fingerprints below are time-scoped observations, not a final frozen release identity.

Final documentation follow-up: 2026-10-02 JST, after the completed run and final saved-state/handoff addendum. The [final facts below](#final-06-evidence-follow-up) supersede the initial pending items; they do not retroactively turn this initial plan into an executed runtime test. See [0.6 verification](../../reports/2026-10-02-v0.6.0/VERIFICATION.md).

The objective remains realistic water and sunlight, not completion of just the shore or solar test subset. Quality has priority over the previously relaxed 60 FPS gate. Native timings, actual Minecraft timings, bounded transport tests, and natural-view acceptance must remain separate.

## Evidence observed at the initial checkpoint, with limited claims

| Proof | Existing evidence | What it establishes / does not establish |
| --- | --- | --- |
| Public water-main visible-bed RED | `build/shore-v0.5-visible-bed-red/` | Paired transmitted deep-bed response is lost at one endpoint: `.100883319974 → 0`, exceeding independently derived `.001669252223` allowance. Actual invocation observation/non-interference and physical/camera visibility are documented in the existing causal review. Not an all-shore defect claim. |
| First water-only GREEN | `build/shore-visible-bed-first-green/` **plus external** `build/shore-visible-bed-first-green.log` | Both paired responses lie in the unchanged physical/plane-pixel bounds; response difference `3.427267e−6`. Not natural-shore visual acceptance or the exact current complete expanded shader. |
| Solar clear RED / GREEN | `build/solar-radiometry-v0.5-red.log`, `build/solar-radiometry-first-green.log` | Actual terrain→deferred beam versus integrated sky disk moves from RGB ratios about `.001357` to `1.000123–1.000527`. Queried C0/C4 storage changes 16F→32F. Synthetic cache, narrow centered view, not Iris pipeline/storage proof. |
| Separate rain RED / GREEN | `build/solar-radiometry-weather-red.log`, `build/solar-radiometry-weather-green.log` | Rain=1 alone changes the admitted beam; ratios about `6.667` become `1.000007–1.000205` when the disk admits the same existing weather factor once. Not physical weather calibration. |
| Ordinary-FOV native validation | `build/solar-ordinary-fov-first.log` | 1600×900, vertical FOV60, centered Sun: RGB ratios `1.000130–1.000533`; actual queried C0/C4=32F. This case passed without requiring a fabricated RED. Not Minecraft frame timing. |
| Additional native coverage observations | `build/solar-1440p-first.log`, `build/solar-1440p-phase-first.log` | 2560×1440/FOV60 and one horizontal `.37`-pixel phase pass the same 2% gate. One phase is not all off-axis/skew/horizon/subpixel coverage. |
| Storage negative control | `build/solar-calibrated-half-storage-negative.log` and its source clone directory | Intentionally forcing calibrated C0/C4 into queried 16F produces finite but severely reduced integrals, ratios `.249944/.255493/.264485`. Do not report this as a shipping-source failure or claim that infinity/NaN was observed. Verify the source clone differs only in the intended declarations. |
| Full native suite | Failed `build/solar-shore-candidate-full-check.log`; corrected-oracle `build/solar-shore-candidate-full-check-calibrated.log` | Preserve both. The failed suite stopped at the pre-calibration underwater disk upper bound. Diagnostic measured red `7372.63` against old `360`; the corrected source-unit presence bound is about `259586`. The calibrated log reaches the 11-program completion trailer; root reports exit0. This validator-unit adjustment was not a shader fix and does not prove underwater radiance/etendue conservation. |
| Storage observer 0.3.4 | `build/benchmark-0.3.4-build.log`, `build/aqualumen-benchmark-0.3.4.jar` | CPU tests/build passed; JAR metadata says 0.3.4 and includes `RenderTargetSnapshot.class`. Actual Iris observation was pending then; the final runtime observation is recorded below. |

Existing independent reviews are `docs/reviews/codex-shore-causal-review.md` and `docs/reviews/codex-solar-coverage-review.md`. Their historical pending paragraphs and older hashes must retain their time scope. The earlier `codex-solar-radiometry-plan.md` is a pre-implementation design record, not the current implementation/status report.

## Initial preservation plan, before another run or build

The initial plan asked root to copy this **allowlist** into immutable, stage-named directories under a new `reports/2026-10-02-v0.6.0/` evidence tree, with path/size/SHA256 manifests. This reviewer did not create those copies. Root's completed bounded archives are linked below; this proposed allowlist is not a claim that every listed historical file has an independently verified complete export. Do not blanket-export `build/`: it also contains launcher/raw-account logs and unrelated private state. Do not overwrite the original failed evidence when obtaining GREEN.

Preserve these entire native trees, including every raw `.rgba32f`, `.pfm`, CSV, expanded shader, vertex, manifest, and embedded log:

| Existing tree | Observed files | Role / overwrite risk |
| --- | ---: | --- |
| `build/shore-v0.5-diagnostic-first/` | 108 | First exploratory/ablation evidence; not acceptance. |
| `build/shore-v0.5-diagnostic/` | 211 | Mutable default diagnostic export destination; repeated runs overwrite existing files and can leave obsolete files. |
| `build/shore-v0.5-causal-first/` | 21 | Initial causal export, including the known CPU palette-reporting error. Preserve, label, do not use its erroneous red field as an oracle. |
| `build/shore-v0.5-causal/` | 21 | Corrected causal export; mutable destination. |
| `build/shore-v0.5-visible-bed-red/` | 14 | Frozen public-output RED. |
| `build/shore-visible-bed-first-green/` | 14 | First GREEN data, but its embedded `red.log` is old RED stdout. |
| `build/shore-v0.5-visible-bed/` | 14 | Current mutable visible-bed destination; contains GREEN data and old RED stdout. |
| `build/shore-v0.5-frozen-source/` | 46 | All names and bytes independently match the shipped 0.5 ZIP. Required RED/baseline source. |
| `build/solar-calibrated-half-storage-negative/` | Inventory at export | Entire intentional negative source clone; pair with negative-control stdout and positive source fingerprint. |

Also preserve these exact top-level files, not just the latest successful line:

```
build/shore-visible-bed-first-green.log
build/solar-radiometry-fixture-aperture-failure.log
build/solar-radiometry-v0.5-red.log
build/solar-radiometry-first-green.log
build/solar-radiometry-weather-red.log
build/solar-radiometry-weather-green.log
build/solar-radiometry-first-probe.h
build/solar-radiometry-weather-probe.h
build/solar-ordinary-fov-first.log
build/solar-1440p-first.log
build/solar-1440p-phase-first.log
build/solar-calibrated-half-storage-negative.log
build/solar-shore-candidate-full-check.log
build/solar-shore-candidate-full-check-calibrated.log
build/solar-underwater-presence-unit-diagnostic.log
build/solar-underwater-calibrated-presence-green.log
build/post-v0.5-shore-default-check.log
build/benchmark-0.3.4-build.log
build/aqualumen-benchmark-0.3.4.jar
```

The first aperture-guard failure is a fixture failure, not the radiometric RED. Its analytic aperture originally used double `1/focal` rather than the supplied rounded-float inverse matrix. Keep it beside the corrected guard and actual subsequent RED.

Before final verification, freeze the exact current `shaders/` + `LICENSE`, `tools/glcheck.cpp`, `tools/solar-radiometry-probe.h`, `Makefile`, observer/Recorder sources, all benchmark-mod tests/descriptors, and `tools/build-benchmark-mod.sh`. Record the compiled `build/glcheck` hash, compiler/link command and context, and each test's return status. A rebuilt executable or new header must not be retroactively assigned to an earlier log. Current `build/glcheck` is itself overwritten by compilation.

Suggested export grouping: `native/shore/{red,first-green,final-candidate}`, `native/solar/{clear,weather,coverage,range-control,fixture-failure}`, `native/full-suite/{failed,calibrated}`, `observer/{source,cpu-build,runtime}`, and `provenance/`. These are proposed destinations, not existing completed exports.

## Source-stale / mixed-time findings at the initial inspection

1. **Do not overwrite the old shipping pack.** At the initial inspection, `tools/build.py` still wrote `dist/Aqualumen-0.5.0.zip`; no 0.6 ZIP/report tree existed. The then-current sources differed from that ZIP in exactly `deferred.fsh`, `gbuffers_water.fsh`, `lib/atmosphere.glsl`, and `prepare.fsh`. This risk was subsequently resolved: the build target now names 0.6, the built 0.6 ZIP is `6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`, and old 0.5 remains `88ff19…`. Both full ZIP hashes were re-read in the final documentation task. Earlier current-source native results must still not be attributed to the installed old 0.5 pack.
2. The three visible-bed directories' embedded `red.log` are byte-identical SHA `3c74210a1fb265133243fc0191e7150762ca5605c677d4c83d1e6acf5e8c5a79`. GREEN baseline/CSV do **not** convert that copied log into GREEN stdout. External first-GREEN stdout is SHA `a3637cdf7d5cca44c16340c14fc9d535c38e8f780fbbe08ef5664efa1c603950`.
3. Frozen visible-bed RED expanded baseline SHA is `d8c8ad0d2f4a56d52d0829f94c3dccb1c183fa5cd0c2a6da86fdde49b5e55303`; first-GREEN/then-current-directory expanded baseline is `6e233e2a29396f45a8eb81220ad4922e925f65e3a13f25ae7e1eef05cd2fc932`. Independently expanding the water source **at this initial checkpoint** with the same public `SHORE_FOAM=0` yielded `f6715e163d65d7c4958da30a7184a0a5e55c2e5e61a68ffc4f3d1c78e16b9682`. Neither old artifact represented that complete Solar-expanded source, even though the water file retained the reviewed solver-fix hash. The requested final-current rerun is now present in `native/v0.6-full-native-check.log` and `native/shore-final-current-artifacts.tar.gz`; the final suite explicitly includes the formerly separate public visible-bed seam. Do not relabel the older first-GREEN artifacts as that newer run.
4. Source/harness changes occurred during this inspection. The first ordinary-FOV header fingerprint was `f9ce5c2ad14caf548f0385d030b2fbba8b8b0933cbe5c6ef88adb1a864aa226a`; latest phase-capable header is different (below). Only the first-clear and weather headers have named saved checkpoints in the inspected top-level files. Preserve/recover and hash-check the exact ordinary-FOV harness if claiming exact historical reproducibility; do not silently use the later phase-capable version as its original. Older C++/binary identity likewise requires a preserved snapshot, not just a filename.
5. `reports/2026-10-02-v0.5.0/real-view/` is a historical 16-scene **1600×900** run of pack 0.5 SHA `88ff19…`, benchmark mod **0.3.3**, and physics mod 0.2.0. It has no new storage-observer field and cannot establish 0.6 visuals or 0.3.4 runtime operation. Its `ordinary-handoff.json` is also a 0.5 point-in-time handoff, not current 0.6 restoration.

Observed source/artifact fingerprints (root must generate the final complete manifest rather than reuse this partial table):

| Path | SHA256 |
| --- | --- |
| `dist/Aqualumen-0.5.0.zip` | `88ff19eed363ff3d25287b3873ed7c0ac7b2ca654074e0365d510fedd07c859d` |
| `dist/Aqualumen-0.4.0.zip` | `5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069` |
| `shaders/lib/atmosphere.glsl` | `89e1d66b88144e018e3d7b012a3e92319209070f38b6e1918c505f965b29ece4` |
| `shaders/gbuffers_water.fsh` | `90f25d146e63e89e32936c306ab68cbba5506d868a4884a8d60db7de943de799` |
| `shaders/deferred.fsh` | `ad9e840596300f4a5ffacc8f212d0e3f00290e06fbe27a347d7bd60a2b1844ef` |
| `shaders/prepare.fsh` | `fa5d6cd1f10e9313dba9a4927d12f19ed9d6443dfbcb7ac1219dd1ae4813c790` |
| `tools/glcheck.cpp` (latest read) | `1a091546fc810fdd544ad595ebe2b78055426112905ba43be2c5353871b536da` |
| `tools/solar-radiometry-probe.h` (latest read) | `6f2b86414ac2b3bbb6e220a2a2a38c276dc0d2f22d0f78ea07a8cffcac1b4c4a` |
| `build/solar-radiometry-first-probe.h` | `9b9fe80cadd7bee32b65b1205f862256b1f7ef9a0fb44a78acccb8d68413c839` |
| `build/solar-radiometry-weather-probe.h` | `b1830be4f6f02f2bae9c66943e16210f647943d3977752f0f7a84c08629dfab3` |
| `RenderTargetSnapshot.java` | `63abc9f494104a3c4d8ff67c93c07cbca05a5e783f2fa5ace3fad8d4790e879e` |
| `RenderTargetSnapshotTest.java` | `5c826fed34a9b7f577506dda6c92afdc802f8cb5db869f1f34eadea95f38c85e` |
| `Recorder.java` | `98dc953802ed850efe6e0b8704a0d90236647346c939bd171ac2f934b2e3e678` |
| `tools/benchmark-mod/fabric.mod.json` | `c257a6d842066c6fbb44733129371d4dea776277f18acd4a732e5ece9b4d01ad` |
| `tools/build-benchmark-mod.sh` | `ed2083bcf311a6a53ebb8884c756aa2df2fb9ce47dc366a1c78f27e7ad11be8f` |
| `build/aqualumen-benchmark-0.3.4.jar` | `23dee6585808ff830cb5aae823751ef682696475bd86c19efb1ea1412b43347b` |

The Java paths abbreviated above are under `tools/benchmark-mod/dev/aqualumen/bench/`, except the test under `tools/benchmark-mod/test/dev/aqualumen/bench/`. The observed Git HEAD is `163d913b742e89097a38f217472ea8fd537f8a4b`; dirty changes mean this commit alone is not candidate provenance.

## Planned actual-Iris export checks (subsequently completed as bounded below)

Freeze candidate ZIP/source first, record its name/SHA, and have root produce a fresh dedicated-world capture with benchmark mod 0.3.4. Existing UUID guard is `b22dbccb-2970-41e6-847f-f183b1ec923d` (AqualumenNaturalV2). Never treat that fixture authority as permission to automate an ordinary world. Export only bounded metadata/CSV/PNG/contact observations (including the expected test-player UUID), not raw launcher arguments, ordinary-account identifiers, or credentials.

`Recorder` adds `iris_render_target_storage` to **run metadata**. `RenderTargetSnapshot` observes existing Iris targets using `get`, not `getOrCreate`; checks `glIsTexture`; queries level-zero actual format/width/height; temporarily binds only the current texture unit; and restores its original 2D binding in `finally`. It performs no texture allocation/pixel write/world mutation. Exceptions export class names only. CPU tests cover missing runtime/storage/target, query failure, restoration failure, and differing main/alt actual formats. At the initial inspection these were source/CPU facts, not successful live Iris reflection; the later actual runtime result is recorded separately below.

For a successful actual storage observation require:

- `available=true`, `bindingRestored=true`, `renderTargetCount≥9`, exactly indices `[0,4,5,6,7,8]`, and valid separate `main` and `alt` records for all six. `available=true` alone is not format acceptance: the observer intentionally reports a mismatch rather than replacing it with the declaration.
- Both C0/C4 images must declare and actually allocate RGBA32F (`0x8814`, decimal 34836); C5/C6/C7/C8 remain RGBA16F (`0x881A`, decimal 34842). Values were checked against the installed GL headers. Compare declarations and actual values independently.
- C0/C4/C5/C8 main/alt dimensions must match the actual captured framebuffer, not the desired window dimensions; C6/C7 must be 1024×512 under current properties. Preserve all 12 image records even if one fails. Texture IDs are runtime identities, not reproducible cross-launch hashes.
- Tie the snapshot to the run timestamp, actual active/nonfallback pack name/hash and mod versions. It is a startup snapshot, not proof of storage across an unrecorded shader reload, every scene, or all frames. `available=false`, absent fields, partial queries, or failed restoration are explicit unavailable/failed evidence, never inferred success.

Storage observation does not read HDR pixels and therefore does not prove finite/unclipped radiance, integrated solar energy in Iris, reflection quality, or performance. Preserve the separate native range/coherence proofs and obtain actual rendered natural-view observations.

Fresh scene audit should independently verify every run/scene pack SHA, active/fallback state, dimension, UUID, expected/actual pose, camera/eye, framebuffer dimensions, settings and sample boundaries. Recompute raw interval count/mean/percentiles/1%-low/stutter from CSV, validate complete PNGs, and report focus/interference. Require the fixed near/deep/tilted upward-eye controls and real contact/moving/dimension observations, not a screenshot filename alone. A before/after causal comparison requires exact matched scene/time/pose/eye/settings, not merely similarly named views.

`tools/report.py::load_run` still deliberately requires exactly 2560×1440. A fresh 1600×900 quality run must be labeled as such and audited without relabeling raw metadata or weakening that verifier. A 2560×1440 **native** solar test is not a 1440p Minecraft benchmark. Describe timing observations honestly; do not manufacture a renewed 60 FPS acceptance guarantee.

## Planned final handoff and open boundary

Root should export a new point-in-time ordinary-runtime handoff for the actual candidate: installed/built ZIP identity, active pipeline/physics, benchmark JAR/marker absent, test client stopped, original ordinary settings restored, fresh normal-account relaunch and visually verified pause. Use bounded booleans/identities rather than raw account logs or argv. Distinguish fixture cleanup from ordinary restoration; ordinary saves can change naturally after normal relaunch. Keep nanosecond timestamps as exact decimal strings (or preserve exact JSON literals with a lossless parser), avoiding JavaScript rounding above 2^53.

Independent final review can accept only the evidence actually exported for the frozen candidate. Remaining physical limits include refracted radiance/etendue convention, local versus exact area/pixel mappings, horizon/skew/occlusion cases, rough-water direct-Sun quadrature, empirical cloud/rain coupling and Moon treatment. Bounded native GREEN, actual Iris storage, and a fresh natural-view handoff can complete an increment; they do not by themselves finish the full realistic-water/Sun goal.

## Final 0.6 evidence follow-up

The candidate and safe handoff are now evidenced; the full visual goal is not complete. Root produced the following bounded exports under [the 0.6 report](../../reports/2026-10-02-v0.6.0/VERIFICATION.md):

- [Historical shore causal archive](../../reports/2026-10-02-v0.6.0/native/shore-causal-artifacts.tar.gz), [first-GREEN stdout](../../reports/2026-10-02-v0.6.0/native/shore-visible-bed-first-green.log), and [final-current shore archive](../../reports/2026-10-02-v0.6.0/native/shore-final-current-artifacts.tar.gz). Preserve the stale embedded `red.log` warning and initial CPU palette-reporting limitation; the separately recorded final suite is the current acceptance stdout.
- [Final source/validation tools](../../reports/2026-10-02-v0.6.0/native/final-source-and-validation-tools.tar.gz), first clear/weather/current probe headers, separate failed/clear/rain/coverage/range logs, and [final complete native suite](../../reports/2026-10-02-v0.6.0/native/v0.6-full-native-check.log). That suite passes the retained regressions, public visible-bed response and all five Solar cases. The older first ordinary-FOV harness history remains time-scoped; a current header must not be substituted silently for its original.
- Completed [16-scene actual 1440p run](../../reports/2026-10-02-v0.6.0/real-view/run.json), [results](../../reports/2026-10-02-v0.6.0/real-view/RESULTS.md) and [independent audit](../../reports/2026-10-02-v0.6.0/INDEPENDENT-AUDIT.md): 14,909 raw intervals, all captures focused and active without fallback, accepted by the unchanged 1440p reporter. Overworld/water/cave/glass mean FPS is 126.5–196.9 over 5-second samples, not a general floor or performance A/B with 1600×900 0.5.
- Actual `iris_render_target_storage` reports available/restored binding, target count 16 and all 12 queried main/alt images. C0/C4 actually allocate RGBA32F (34836) at 2560×1440; C5/C8 use RGBA16F (34842) at that size; C6/C7 use RGBA16F at 1024×512. This is the observed initialization boundary, not continuous monitoring, HDR readback or an Iris solar-energy integral.
- [Ordinary handoff](../../reports/2026-10-02-v0.6.0/ordinary-handoff.json) and [independent final addendum](../../reports/2026-10-02-v0.6.0/INDEPENDENT-AUDIT.md#final-saved-state-and-ordinary-handoff-addendum): fresh normal-account 0.6/physics 0.2.0 launch paused, benchmark JAR/marker inactive, options byte-restored, and saved TEST audits showing 390 approved AIR cells/no journal before and after stop. TEST Save/Quit stalled and required scoped termination; this is not a clean-exit or shutdown-fix claim. Ordinary save/options backups stay private in `build/`, and ordinary saves naturally resume after normal relaunch.

The [actual-image audit](codex-v0.6-visual-audit.md) still finds cyan/jagged natural shores and stylized reflection ribbons. Motion/wakes, coherent spatial cloud shade, and general refracted radiance/index-squared/etendue transport remain unmet. These final facts supersede the initial runtime/lifecycle pending assertions, not the goal's remaining requirements.
