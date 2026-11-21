# Independent v0.6.0 capture-data audit

CPU-only, read-only inspection of the completed `water-v0.6-real-view-1440p` run. This document is the only audit write. No game control, GPU test, source/configuration modification or process action was performed.

## Provenance and acceptance boundary

- The live run started at `2026-10-01T22:38:01.377989283Z` and its own `complete.json` records `2026-10-01T22:40:50.198622557Z` (October 2 in JST).
- All **82 raw evidence files** in `real-view/`—run/completion metadata plus 16 sets of CSV, scene JSON, PNG and two physics files—were byte-identical to the original Lab run at audit time. Generated `RESULTS.md` is not included in this raw-file count.
- Public `tools/report.py::load_run` accepted both the original run and the copied run: 16 scenes, no abort record. Independently parsed CSVs and additional metadata/storage checks also passed.
- Installed ZIP: `6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`. This equals the requested, run-recorded and every scene-recorded pack SHA. The live Iris selection was `Aqualumen-0.6.0.zip`, with shaders enabled; run/scene records all report active without fallback.
- Installed benchmark JAR: `23dee6585808ff830cb5aae823751ef682696475bd86c19efb1ea1412b43347b`; runtime mod metadata reports benchmark `0.3.4`. The JAR hash was independently read from disk; the run does not itself record a loaded-JAR byte hash.
- Exact disposable world: `AqualumenNaturalV2`, UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`, seed `308060`, vanilla overworld noise generation. Recorder's unchanged guard requires the identified sole local player, integrated singleplayer server and no LAN publication; successful completion is evidence those guards passed, not an independent new server query by this audit.
- Metadata hashes: `run.json` = `ce007088976254e7ff57b41b75eb8c72e90410a99b86f7f91aa651686c4b83dd`; `complete.json` = `fa53ec8666f4fe1781a867545e7b7dcd54c58cce70fc33fff8ba2e0b12a2869a`.
- Reporter source inspected: SHA `716e7dbbb58c736ad076f317d214f23ba542bc0e91b1b480865eb1d37201b31c`.

## Actual Iris storage observation

The initialization snapshot reports `available=true`, `bindingRestored=true`, a render-target count of 16, and complete main/alt queries for six requested targets. This does not claim all 16 slots were allocated. All 12 queried texture IDs are positive; declared and actual GL formats and sizes match.

| Targets | Declared format | Actual GL internal format, main and alt | Size, main and alt |
|---|---|---:|---|
| C0, C4 | RGBA32F | 34836 | 2560×1440 |
| C5, C8 | RGBA16F | 34842 | 2560×1440 |
| C6, C7 | RGBA16F | 34842 | 1024×512 |

This establishes actual storage allocation at the observed initialization boundary, not continuous monitoring or an assertion that stored pixel values never overflow. It is distinct from the native radiometric tests and from the visual appearance of the solar disk.

## CSV and configuration checks

Configuration: NVIDIA RTX 3080 Ti, GL `3.2.0 NVIDIA 580.173.02`; Minecraft 1.21.1, Iris 1.8.8, Sodium 0.6.9, Java 21.0.7. Window and actual framebuffer are 2560×1440, render/simulation distances 12/6, VSync false, recorded frame-limit setting **260**. Iris pipeline and effective vanilla cloud settings are both OFF. Metadata reports ZGC and 2 GiB initial / 6 GiB maximum heap.

Each scene requested 5 s warmup and 5 s sample. The independent parser verified sequential zero-based frame indices, strictly positive integer nanosecond intervals, finite `ms = ns / 1e6`, and the sum of intervals against `recorded_seconds`. All seven recomputed metrics match scene JSON; no mismatches were found. Reported sample durations range from 5.000095097 to 5.006627211 s.

| Scene | Frames | Mean FPS | Slowest-1% mean FPS | P99 ms | Worst ms |
|---|---:|---:|---:|---:|---:|
| ocean-day | 695 | 139.126508 | 111.687771 | 8.791770 | 9.283968 |
| coast-day | 694 | 138.779966 | 107.921142 | 8.825193 | 9.848641 |
| river-day | 680 | 136.140247 | 105.851144 | 9.306159 | 9.649876 |
| ocean-dusk | 651 | 130.328901 | 100.758249 | 9.533858 | 10.601779 |
| ocean-night | 717 | 143.586397 | 106.394923 | 8.961430 | 9.892353 |
| ocean-rain | 632 | 126.506900 | 98.386187 | 9.823673 | 10.559639 |
| underwater | 778 | 155.717297 | 111.799260 | 8.464043 | 10.290363 |
| underwater-up-near | 984 | 196.942996 | 132.914947 | 7.185274 | 8.219622 |
| underwater-up-deep | 966 | 193.331982 | 128.821795 | 7.063435 | 9.655777 |
| underwater-up-tilt | 981 | 196.274158 | 128.328822 | 7.084104 | 8.652798 |
| moving-view | 676 | 135.363482 | 101.484279 | 9.510744 | 10.322263 |
| boat-contact | 689 | 137.947161 | 107.853637 | 8.964636 | 9.679603 |
| cave-water | 826 | 165.323955 | 113.250354 | 8.315283 | 10.510377 |
| glass-layers | 760 | 152.006002 | 104.674533 | 8.991206 | 10.488926 |
| nether-view | 2106 | 421.035532 | 210.006921 | 4.137343 | 6.451712 |
| end-view | 2074 | 414.874967 | 229.517029 | 3.943738 | 5.652196 |

Total: **14,909 intervals**, **79.948394955 s** recorded; interval-weighted aggregate 186.482793 FPS. The aggregate includes unusually fast dimension views and is not representative of a typical overworld workload. Worst interval was 10.601779 ms in dusk; all scenes had zero intervals above the 16.667 ms reference. These are short observed render-tail wall-clock intervals, not GPU-only timings, a general FPS floor, or an appearance/physical-correctness score. The numerical limit 260 is recorded without asserting how Minecraft applies that setting; dimension measurements exceed it.

Workloads are **15 warmed views**, including a rotating `moving-view`, and **one scripted boat-contact scene**. No chunk-traversal scene was measured. One PNG from a moving scene is not temporal acceptance.

## Camera, focus and contact gates

- All 16 scene records report `window_focused=true`, current-local-player camera identity, and camera locking. Measured rendered-camera and player angles are identical in every capture; static expected angles match within 0.05°. `moving-view` records actual yaw 14.940323° / pitch 9°. Focus is recorded at capture, not continuously throughout every interval.
- Nether and End records have their correct dimensions; all other records are overworld. Fixed coordinates and the actual rendered-camera pose passed the capture guards. Explicit first-person eye/submersion fields are available for the three upward-water scenes; they are not assumed for every scene merely from the camera-identity flag.
- Upward near/tilt eyes are at `(448.5,62.38900000476837,-383.5)`, deep eye at `(448.5,59.63900000476837,-383.5)`. Actual fluid surface is 62.88888931274414; measured eye depths are 0.4998893079757707 / 3.2498893079757707 / 0.4998893079757707 m. Rendered camera differs from the measured eye by only `1.1920928955078125e-7` m. All three explicitly record first-person, head submerged, touching water and camera medium WATER, yaw −45°, pitches −90°/−90°/−65°, frozen client/server time 6000 and no terrain placement.
- Boat contact has six diagnostic samples; all show an active bridge and one contact. Four have nonzero force (`0.0338`, `0.0140`, `0.0323`, `0.0188`), maximum 0.0338. The first two force samples are zero. The recorded driver is integrated-server boat translation at 6 m/s and 20 Hz, not manual vanilla rowing. This proves nonzero measured contact input in part of the sample, not physically realistic wake appearance.
- Coast separately shows up to two uncontrolled ambient contacts and force 2.2167; these must not be attributed to the scripted boat. Other scene maxima are zero. Cave's active bridge reports local surface 14.8889; Nether and End terminal diagnostics are inactive with zero contacts, as expected for non-overworld operation.

## PNG completeness and provenance

All **16 PNGs** passed the reporter's bounded PNG checks: signature, exact 2560×1440 dimensions, supported pixel format, all chunk CRCs, ordered IDAT/IEND, complete bounded zlib decode and legal scanline filters. Each copied scene PNG is byte-identical both to the live run export and the completed original native screenshot. This addresses incomplete-export risk; it does not substitute for visual review.

| Scene | PNG SHA-256 |
|---|---|
| ocean-day | `380d62ddbb688f5210b6577b6722875c21498f416727fb455f091fcafd58706d` |
| coast-day | `523a7cf519748e1c23c62c708f045eaf734869bffdcf8106ddf07871e215648a` |
| river-day | `a8d819392d659d845748d5e9f87363c6978dc0bb340079b5541a03405003ca59` |
| ocean-dusk | `6ec96884e9ec48a0bf52824f6411f0ec8e6742133c44d7a1b7c9d775f9bf12eb` |
| ocean-night | `739faf424d3c70575a869eafdfd840ef45071d53456624d7e4b4eddb4c26932c` |
| ocean-rain | `ff8db269f6248e3ffecd7d6bb366211f1c1fc6dac4419538369c5daa274d01a4` |
| underwater | `37a4a703e2aa9d5c9fec7afd6520fc23958d9e04fec5126fc690a5f31d26625f` |
| underwater-up-near | `a2264c12220a18c38eb9091a0b6403ba681d8ec295a9338d255332c5ca983553` |
| underwater-up-deep | `49531e1c79b2e2e96cd27fe9aab499723f709fcb17cc46bd93f15dffcbe7e254` |
| underwater-up-tilt | `f9873d647e58682e2d0e85282bdcd1c7dc6ca7657e54682f2762672a753543e9` |
| moving-view | `bb1c65490e0539adc3355cb63c08de6afeec59560d5942ad1509cbbfc3431960` |
| boat-contact | `f8439eccd9361f3a34da57b30d225bb2f2238d849e94a3b46eba8aa816417340` |
| cave-water | `43bae00c31fb84e52ab211460f58b49d399604c4719bb7cfcfe27e623595fe3a` |
| glass-layers | `6ad28c9c9bf06656fe897c1f0264988dd482015489859a0dc34c0507e08e60f1` |
| nether-view | `d6d178017d9db061757bc0a92fd01a57d899f42b34f35cc6f0496354d2255337` |
| end-view | `5a390fbaf8d3b6b19aca207c93fc99c9e44d3a1161e0bb7b3609a5817cfccde8` |

## Cleanup and outstanding acceptance

The run's complete record confirms fixture cleanup. The scoped opaque-fixture journal was absent at inspection; no abort record exists. Recorder's finishing path waits for the current overworld/local-player camera before its final guard and completion record. This is completed runtime cleanup evidence, **not yet an independent post-stop disk-save audit** of reserved cells or proof that the server/process has exited.

At this audit stage, TEST Save/Quit, persisted fixture-state verification and ordinary-client handoff remain pending under root's lifecycle ownership. No current ordinary-world/options byte invariance is inferred from earlier snapshots or a paused process. Visual shoreline acceptance, temporal behavior, complete solar radiometry and all physical fluid effects are outside this capture-data audit; sixteen valid short views do not establish the global realism goal.

## Final saved-state and ordinary-handoff addendum

This section supersedes the pending lifecycle items above; it does not broaden visual or physical acceptance.

- Root's before/after TEST-stop Anvil audits at `22:46:56.780766Z` / `22:48:03.453704Z` both identify the exact V2 UUID and seed and report all **390 approved unique reserved cells** as exact `minecraft:air`, zero non-AIR cells and no pending ownership journal. Both report cleanup PASS, no world writes and no control requests.
- I independently reran the bounded, read-only `tools/audit-fixture-air.py` at `2026-10-01T22:56:30.332453Z`: the same 390 exact AIR cells, absent journal and cleanup PASS were reproduced. The actual saved region SHA was `4b68b92130093f0f9a73c82ada95b4dc984e35b4f6a988f0c79e551bcd945da5`, matching both root snapshots. This is a specific reserved-cell audit, not whole-world/entity integrity or a disk audit of every possible temporary fixture location.
- Raw CSV nanosecond columns were preserved byte-for-byte in the 82-file export comparison. Exact integer `ns` values were parsed directly; timing validation did not reconstruct them from rounded millisecond values.
- Actual ordinary `options.txt` is byte-identical to `build/snapshots/v0.6.0/options.txt`, SHA `02516270fea53cc286dceb1d5eca457f2ecc2e0ab6d2e1b15b01c4032307e5f0`. Read-only inspection confirms override size 1600×900, frame-limit setting 120 and pause-on-lost-focus true. Both normal handoff PNGs pass the strict bounded PNG checker at 1600×900; the paused screenshot was independently viewed and shows the native Japanese game menu over the normal scene.
- There are zero active benchmark JARs in the Lab `mods/` directory and the enable marker is absent. Installed ordinary ZIP remains `6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`; installed physics 0.2.0 JAR is `1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e`. These disk hashes were independently re-read, not only copied from the handoff record.
- A PID/PPID/comm-only read confirms Java `2460455` exists with parent `2460359` (`prismrun`); exact TEST Java `2448791` and TEST launcher `2448688` are absent. This proves process presence/absence at inspection, not sustained responsiveness. Root's handoff record separately verifies a normal, non-offline-TEST launch, normal-world log, active selected pack/pipeline and physics initialization, with no observed shader-error/fallback log. No account data or process argv was read by this audit.
- Root records that the ordinary save tree matched its private post-save backup **before** the normal relaunch. I did not inspect that private backup. The record explicitly allows ordinary autosaves to resume afterward; neither this audit nor that earlier comparison claims the current ordinary save tree remains byte-identical. No ordinary-world automated camera/time/terrain actions are recorded. Launcher window dimensions were restored while intentional runtime/playtime bookkeeping was preserved; whole launcher configuration byte equality is explicitly **not** claimed.
- TEST manual Save/Quit again stalled: the saved thread excerpt shows Render thread inside `MinecraftClient.method_18096` via `glfwSwapBuffers`, while Server thread remains in its parked server loop. Root records scoped TERM of only the identified TEST Java and its own TEST launcher after completed capture/cleanup checks. This was **not a clean process exit**, and the shutdown defect/causal attribution remains unresolved. The excerpt does not establish that Recorder caused it or that a fix was applied.

Final evidence identities: `ordinary-handoff.json` SHA `7efac8deeb59cdf33d044cd5f8ef2fd086592ab6f472ffb5ae02ab1c022c0fee`; before/after AIR audit SHAs `b7af83c86fb02769ba4c6351fcf55d44ff090283dd8586f82f2a76fc2b87bad6` / `231b6ff03435f12fad33e7752b137d1e755ddb46279ff8f2a500137f6f7efcb0`; thread-excerpt SHA `a5299b68c5d32a9818887f7e928080d8b3b684bf1637fb972b302dc44fe6cc5d`. Normal current/paused PNG SHAs are `25945ee5ba10cfa4ec2f5842b92c5c1280982248fb0e4f3f0b768f623f562ba7` / `69856a9ba9d9f73d40c6361d9d97485a78054837b8b9954b2f2617460592ecf2`.

The full convincing-water/sunlight goal remains open. This addendum closes the bounded saved-cell and ordinary-handoff evidence checks, not temporal shoreline appearance, full physical validation or shutdown reliability.
