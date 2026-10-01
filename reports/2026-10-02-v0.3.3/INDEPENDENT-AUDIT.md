# Independent Minecraft runtime audit — v0.3.3

Audit date: 2026-10-02 JST. Evidence timestamps below are UTC.

Result: all **16 accepted PNGs and 21,132 raw render-loop intervals** passed the independent checks. The visible rectangular underwater sky seam is absent in all three new-pack comparison views. This is a bounded rendering/compatibility observation, not a photorealism certification or an FPS guarantee.

## Provenance and scope

The benchmark-tooling agent independently inspected the saved captures, compared all six A/B images visually, and subsequently viewed all ten compatibility images. A separate read-only audit agent recomputed the CSV metrics and validated PNG integrity and pose metadata. Neither audit operated Minecraft, sent benchmark requests, changed settings/worlds, or ran GPU tests. Only this report was written.

Accepted sources:

| Folder | Run ID | Metadata start UTC | Completion UTC | Scenes / PNGs | Raw intervals |
|---|---|---|---|---:|---:|
| [before](before/RESULTS.md) | `underwater-v0.3.2-before` | 2026-10-01T17:56:31.642924769Z | 2026-10-01T17:57:02.698047638Z | 3 | 3,838 |
| [after](after/RESULTS.md) | `underwater-v0.3.3-after` | 2026-10-01T17:58:48.584421848Z | 2026-10-01T17:59:19.825680482Z | 3 | 3,693 |
| [compatibility](compatibility/RESULTS.md) | `compatibility-v0.3.3-10` | 2026-10-01T18:01:13.313578099Z | 2026-10-01T18:02:58.692057061Z | 10 | 13,601 |
| Total | | | | 16 | 21,132 |

Every run has a matching complete record, no abort record, and `fixture_cleanup_complete=true`. Compatibility ends with the End view; completion includes the guarded return to the Overworld. Root owns the runtime lifecycle evidence; the independent audit checks the recorded completion and scene identities.

Common recorded environment: Minecraft 1.21.1, Iris 1.8.8+mc1.21.1, Sodium 0.6.9+mc1.21.1, Java 21.0.7, benchmark instrumentation 0.3.3, physics bridge 0.2.0, NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2, GL `3.2.0 NVIDIA 580.173.02`. Window and framebuffer are both 2560×1440, render distance 12, simulation distance 6, VSync false, frame-limit **setting 260**. Recorded ZGC collectors are Minor Cycles/Pauses and Major Cycles/Pauses; initial/max heap 2/6 GiB. Iris pipeline and effective Minecraft cloud settings are both OFF; the pack's procedural clouds remain visible.

All three runs use the same dedicated natural vanilla noise world `AqualumenNaturalV2`, UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`, seed 308060, and identified offline actor UUID `b9b618bd-671c-303a-9900-ce0b3f6de348`. Runtime guards require the local integrated server, no LAN publication, and exactly the identified local player/camera. This actor is not an assertion about a user's ordinary-world identity.

## Pack and instrumentation identity

| Evidence | Exact SHA-256 | What was independently checked |
|---|---|---|
| Before installed `Aqualumen-0.3.2.zip` | `7b5bdfb78e79b3214ca2a1fca77657c88680dbf46ef1b875dd95c0eeb652a9c2` | Installed file hash equals before run/scene metadata and expected pack hash. |
| After/compatibility installed `Aqualumen-0.3.3.zip` | `ff81efa32c96f3b1c2c76c1c55fe6e32ed29f1344e67a239afeeccca980583e5` | Installed file hash equals after/compatibility run/scene metadata and expected pack hash. |
| Installed benchmark `aqualumen-benchmark-0.3.3.jar` | `78d3b56877c0d3f9a8a9133aed8865ee7c42498bd7ed19a7d1a43cefd71f9c10` | Independently hashed the installed file during the audit. The three run metadata files record benchmark version 0.3.3, **not its JAR SHA**. Root's installation/continuous-client record supplies the historical runtime link; the SHA cannot be reconstructed from run metadata alone. |

All scene records report the expected active pack without Iris fallback. The before/after actual pose, eye, rendered camera, angles and underwater measurement objects are exactly equal for corresponding scenes. Pack identity changes; animated clouds and exposure state are not frozen or pixel-identical controls.

## Actual upward-view geometry and submersion

All upward views are at X=448.5, Z=−383.5, in `minecraft:deep_ocean` with 16 water blocks in the inspected natural column. No terrain placement was requested. Measured fluid surface Y is **62.88888931274414**, compared with the fixed reference 62.8889. Client and integrated-server times both equal the requested frozen 6000 in every A/B capture.

| Scene | Requested player Y | Actual player Y | Actual eye Y | Actual rendered camera Y | Actual yaw / pitch | Requested eye depth m | Measured eye depth m |
|---|---:|---:|---:|---:|---|---:|---:|
| `underwater-up-near` | 60.7689 | 60.769 | 62.38900000476837 | 62.38899988555908 | −45° / −90° | 0.5 | 0.4998893079757707 |
| `underwater-up-deep` | 58.0189 | 58.019 | 59.63900000476837 | 59.63899988555908 | −45° / −90° | 3.25 | 3.2498893079757707 |
| `underwater-up-tilt` | 60.7689 | 60.769 | 62.38900000476837 | 62.38899988555908 | −45° / −65° | 0.5 | 0.4998893079757707 |

The values above hold in both packs. Eye/camera displacement is **1.1920928955078125e−7 m**, below the 0.05 m guard tolerance. Actual player and camera angles agree with the locked requested angles. Every capture records first-person=true, eye-match=true, touching-water=true, submerged-in-water=true and actual rendered camera submersion `WATER`. These are runtime observations: Entity `method_5869` is the head-underwater predicate; `method_5799` is body contact only; Camera `method_19334` reports the rendered medium. API ownership and signatures were checked against local mappings and the actual remapped Minecraft JAR before implementation.

## Independent raw timing recalculation

Every CSV was checked for consecutive frame indices starting at zero, positive integer nanoseconds, consistent milliseconds, and duration equal to the sum of raw nanoseconds. Frames, mean FPS, slowest-one-percent mean FPS, P99, maximum interval, minimum instantaneous reciprocal FPS and reference-budget exceedance count were independently recomputed and matched the scene JSON. Table values are rounded for display; exact raw values remain in the CSV/JSON files.

| Run | Scene | Intervals | Mean FPS | 1% low FPS | P99 ms | Worst ms | Minimum instantaneous FPS | >16.667 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| before | underwater-up-near | 1,284 | 256.774910 | 166.914040 | 5.453531 | 7.808676 | 128.062683 | 0 |
| before | underwater-up-deep | 1,263 | 252.651732 | 155.760985 | 5.817687 | 8.598103 | 116.304724 | 0 |
| before | underwater-up-tilt | 1,291 | 258.323790 | 167.903712 | 5.561604 | 7.177648 | 139.321404 | 0 |
| after | underwater-up-near | 1,241 | 248.306403 | 170.558559 | 5.625845 | 6.285588 | 159.094105 | 0 |
| after | underwater-up-deep | 1,204 | 240.820963 | 161.056060 | 5.856921 | 6.961871 | 143.639547 | 0 |
| after | underwater-up-tilt | 1,248 | 249.705227 | 160.556085 | 5.848835 | 7.211332 | 138.670637 | 0 |
| compatibility | ocean-day | 848 | 169.639634 | 122.834164 | 7.937258 | 8.462468 | 118.168837 | 0 |
| compatibility | coast-day | 833 | 166.631314 | 121.246028 | 8.082702 | 8.533431 | 117.186159 | 0 |
| compatibility | ocean-dusk | 854 | 170.879195 | 123.025953 | 7.780283 | 8.921733 | 112.085847 | 0 |
| compatibility | ocean-night | 886 | 177.339274 | 126.514509 | 7.552123 | 8.247292 | 121.251921 | 0 |
| compatibility | ocean-rain | 780 | 156.062299 | 112.846542 | 8.566724 | 9.611000 | 104.047446 | 0 |
| compatibility | underwater | 982 | 196.543208 | 136.406319 | 6.888373 | 8.209912 | 121.803985 | 0 |
| compatibility | cave-water | 1,043 | 208.579142 | 131.976753 | 6.981498 | 9.648130 | 103.647028 | 0 |
| compatibility | glass-layers | 838 | 167.711552 | 114.227244 | 8.147775 | 10.417690 | 95.990570 | 0 |
| compatibility | nether-view | 3,330 | 666.087104 | 336.865807 | 2.707439 | 3.644735 | 274.368370 | 0 |
| compatibility | end-view | 3,207 | 641.458818 | 374.358698 | 2.479810 | 3.653942 | 273.677032 | 0 |

| Run | Scene | Sum of recorded intervals s | Actual sample elapsed s |
|---|---|---:|---:|
| before | underwater-up-near | 5.000488565 | 5.003956907 |
| before | underwater-up-deep | 4.998976218 | 5.002030921 |
| before | underwater-up-tilt | 4.997603983 | 5.000594996 |
| after | underwater-up-near | 4.997857423 | 5.001912149 |
| after | underwater-up-deep | 4.999564755 | 5.002963135 |
| after | underwater-up-tilt | 4.997892967 | 5.001411895 |
| compatibility | ocean-day | 4.998831816 | 5.003821934 |
| compatibility | coast-day | 4.999060376 | 5.004981147 |
| compatibility | ocean-dusk | 4.997682711 | 5.000591189 |
| compatibility | ocean-night | 4.996073230 | 5.000775326 |
| compatibility | ocean-rain | 4.998004036 | 5.003084735 |
| compatibility | underwater | 4.996356844 | 5.002110270 |
| compatibility | cave-water | 5.000500008 | 5.004002734 |
| compatibility | glass-layers | 4.996674302 | 5.002202924 |
| compatibility | nether-view | 4.999346155 | 5.000653837 |
| compatibility | end-view | 4.999541532 | 5.001113523 |

Each scene requests 5 s warmup + 5 s sample. One initial boundary is discarded; setup, serialization and screenshot writing occur outside the measured interval. These are **render-loop wall-clock intervals**, including CPU work, rendering, pacing and chunk activity, not isolated GPU timer results. They are short fixed-view samples, not a traversal/boat stress test or normal-play minimum-FPS guarantee. No other GPU jobs were scheduled during root's timed runs. The recorded 260 selector is not presented as an enforced cap: Nether/End intervals demonstrably imply higher rates. Zero intervals over the 60 FPS reference budget describes only these samples and is not the quality acceptance gate or a sustained-floor promise.

## PNG completeness and visual findings

All 16 images pass the production report's independent bounded validation: exact 2560×1440 RGB/RGBA8 non-interlaced format, at most 16 MiB encoded bytes, chunk ordering/CRC, complete IEND with no trailing bytes, bounded exact-size zlib scanlines and valid filter markers. Damaged CRC, dimensions, truncation, oversize and zlib cases were also rejected in memory. All six A/B exported PNG hashes were compared with their corresponding native Minecraft screenshots and match exactly; no A/B export recovery or image editing was performed.

| Run | Scene | Encoded bytes | SHA-256 |
|---|---|---:|---|
| before | underwater-up-near | 1,787,490 | `5e623a2edf4797234fea8d6beb3fd67aab4fa0b76a34af699ba7bfc388d444e3` |
| before | underwater-up-deep | 1,668,541 | `0b46504c0cb30e6b8cd7cb61aa21532702cf0bad2a28b3f23742ba4c0f0d0038` |
| before | underwater-up-tilt | 1,470,970 | `85ed5fd110c8b6194b617893a66608238960168a1b116d0a3bb919394d6e2d83` |
| after | underwater-up-near | 2,684,632 | `7b7bad1cc7eb767533b664692fb256e1fc45c3ca725db29175c6a1cc022269d6` |
| after | underwater-up-deep | 2,490,606 | `a85ebae83d5f3c86a7d9924323c1479e723642648128f78aaab064d9d5881379` |
| after | underwater-up-tilt | 1,955,019 | `f265a1b524eb47f059f3a2bc488d6482596b3ab4634aa4348196b6d65b53af5f` |
| compatibility | ocean-day | 4,500,251 | `bb76fb7bdd6a794ec74898a34ef6b943c705a0fdf3b6c7eb6ddbf61b3f0e2849` |
| compatibility | coast-day | 5,116,185 | `c0ae868d731cdecbd64c1144b6bdd92782af573a15f080939361104832ed0420` |
| compatibility | ocean-dusk | 4,323,594 | `0175ad73f8bb6337cf59b637b26b07cade8cb385d31b87dde7ab245393c221df` |
| compatibility | ocean-night | 3,637,545 | `5771f8c3cd98a9f94a6021b0997c0a9bf9a8ca5e9a5361670b5b90f7cfaf4953` |
| compatibility | ocean-rain | 5,092,397 | `8756491370b29724da210985294eb9b9fe1e3647755ace4f9aa768992c5cf548` |
| compatibility | underwater | 953,096 | `0cf3da0a7867db2faec766ad8157af0a1ba97e107dee3a092160ba22f94e6052` |
| compatibility | cave-water | 1,198,311 | `6817d46192e9b2c2d063ff461892c7a38c2e493b9ad23760056effb519ab1fc7` |
| compatibility | glass-layers | 5,116,180 | `b436e5558df14073bd8863f501be98fd6d3824fc15d7adabf54f3390176c5813` |
| compatibility | nether-view | 4,421,722 | `33a1723466b8180b42a0652e923ba169561b39b9832fd2f55d269e33cd1cdaab` |
| compatibility | end-view | 1,751,188 | `a6f30182b2c361ca2b7fb99b54c6973e0ad1bf77718041a42ef18b61b46c6b49` |

Visual inspection:

- Before: a large straight-edged inset rectangle produces discontinuous/repeated cloud mapping in near, deep and tilted upward views. After: that rectangular boundary is absent in all three, while the rounded Snell window and dark outer reflection region remain. Deep water retains its blue attenuation. Small square flecks occur in deep captures before and after; this audit does not identify their cause or attribute them to the removed seam.
- Compatibility: ordinary ocean reflections, dusk/night/rain appearance, dark underwater terrain, cave water and layered glass remain visible. Nether and End show their appropriate non-Earth environments without the Earth sky/cloud field. The scene dimension records agree: Nether/End respectively, other eight Overworld.
- Strong cyan shallow-coast color, sharp screen-space-looking refraction boundaries and stylized/soft procedural clouds remain quality limitations. The images do not certify photorealism, arbitrary off-screen occlusion or all physical optics. Animated cloud/exposure differences prevent pixel-exact A/B claims; root's separate native rendering regressions provide the causal shader checks, not this visual/timing audit.

## Independent post-stop saved-world cleanup

After root confirmed the dedicated test client had stopped, this agent ran the checked-in read-only bounded Anvil parser, without game/server/control requests. At **2026-10-01T18:12:25.893955Z**, actual saved block-state palettes/packed indices confirmed:

- Exact approved V2 UUID and seed 308060; approved near/far/west-air wall and target reservations only.
- **390 distinct cells across eight chunks, all exact `minecraft:air`**, no non-AIR cells and no pending fixture journal; cleanup pass true.
- Region `r.0.-1.mca`, 9,388,808 bytes, SHA-256 `3947b32012add7e93d6a4e5fa97ee93729bfd365bed8bf78a9a2bba671a530a3`.
- The independent current read matches [root's persisted post-stop evidence](persisted-air-post-stop.json), including plots and region hash. This is a fresh disk check, not merely the runtime cleanup flag.

The region hash changed during SaveQuit; pre/post byte identity is **not** assumed or claimed. The audit itself performed no world writes. Root owns the process-stop, instrumentation-disable, ordinary-world restoration and options-backup comparison evidence; this report does not independently claim those lifecycle actions were performed by the auditor.
