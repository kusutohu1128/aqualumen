# Independent v0.5 real-image visual audit

Reviewed 2026-10-02. **The convincing-real-shallow-water goal is still unmet.** All sixteen candidate stills render their intended scenes, but the coast and river retain strongly cyan/mint receivers and sharply serrated dark/clear water bands. The new incident-Sun transport has bounded numerical evidence; these real images do not demonstrate that those dominant shoreline appearance problems are solved.

This reviewer inspected the sixteen exported candidate PNGs, the same-resolution 0.4 coast reference, and selected 1440p 0.4 river/ocean/underwater/cave/glass/dimension references. Independent read-only metadata, bounded PNG integrity, CSV recalculation and source/ZIP checks were performed. No GPU test, game/control request, lifecycle operation, configuration change or shader edit was made. Only this review document was written.

## Provenance and comparison boundary

Candidate evidence is under [`real-view`](../../reports/2026-10-02-v0.5.0/real-view/run.json), run `water-v0.5-real-view`, started `2026-10-01T20:29:41.401766432Z` and completed `2026-10-01T20:32:25.565043684Z`. It requested five seconds warmup and five seconds sample per scene. All records identify active `Aqualumen-0.5.0.zip`, no fallback, and SHA-256 `88ff19eed363ff3d25287b3873ed7c0ac7b2ca654074e0365d510fedd07c859d`. The independently hashed `dist/Aqualumen-0.5.0.zip` matches that recorded actual/expected identity; this is an artifact audit, not inspection of the subsequently resumed ordinary game.

The recorded test scope is `Aqualumen Lab/AqualumenNaturalV2`, world UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`, seed `308060`, vanilla `minecraft:noise/overworld`, player UUID `b9b618bd-671c-303a-9900-ce0b3f6de348`. The existing recorder requires the integrated singleplayer server and rejects LAN publication; no guard relaxation was used for this audit. Minecraft 1.21.1 / Iris 1.8.8 / Sodium 0.6.9, benchmark 0.3.3, physics 0.2.0, Java 21.0.7, NVIDIA RTX 3080 Ti / driver 580.173.02 are recorded. Window and framebuffer are **1600×900**, render/simulation distances 12/6, VSync false, recorded frame-limit setting **260**, default pack options, and ZGC with 2/6 GiB initial/max heap. Effective Iris/Minecraft clouds are OFF; shader procedural clouds remain enabled.

The 0.4 coast reference is [`temporal-run/coast-day.png`](../../reports/2026-10-02-v0.4.0/temporal-run/coast-day.png), SHA-256 `61d01c96f5368b9afddadb16e8302bb8eb37f86ae3bbc4813f24e7fc95f02d6d`, from `water-v0.4-full-motion`, active 0.4 ZIP SHA `5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069`. Its actual player/camera positions, rotations, world, site, dimension and 1600×900 window/framebuffer exactly equal the candidate coast record:

| Player XYZ | Rendered camera XYZ | Yaw / pitch |
|---|---|---|
| `(-191.5,64.1,320.5)` | `(-191.5,65.71999988555908,320.5)` | `0 / 9` |

**This is not a strict causal pixel A/B.** Wave/cloud phase continued and entities moved; two turtles are visible in the candidate coast. Both stationary coast runs have actual contacts: old maximum two / force `2.2749`, new maximum two / force `2.1906`. They are not contact-free wind controls. The reference coast sampled thirty seconds versus the candidate's five, so their timings are not a controlled performance pair either.

Other 0.4 references are from [`after`](codex-v0.4.0-visual-audit.md), at **2560×1440**, versus this run's 1600×900. Static scenes have equal recorded actual positions/rotations, but resolution/footprint, phase and entity differences prevent pixel or causal performance comparison. The moving/boat views are not exact static-pose pairs. The old image hashes and visual limits remain recorded in the prior audit; none of those historical artifacts were rewritten.

## What the stills show

| Candidate scene(s) | Independent visual observation | Bounded conclusion |
|---|---|---|
| Coast | The large saturated cyan foreground, pale mint/yellow shallow steps, broad serrated dark/clear bands and bright shore edging remain in both 1600×900 references. Individual outlines and animal positions change. | No convincing removal of the dominant cyan/shore artifacts; not shallow-water visual acceptance. |
| River | Mint/cyan foreground still contrasts with gray-blue reflective stripes, distorted vegetation reflections and a bright white bank edge. Coarse stepped/banded transitions remain. | Same qualitative limitation as 0.4; the resolution change prevents fine aliasing comparisons. |
| Ocean day | Gray-blue cloud reflections, fine elongated wave lines, dark foreground patches and a narrow beige horizon band remain. No missing-water surface or camera-image rectangle is apparent. | Open-ocean compatibility retained in this view, not calibrated sea appearance. |
| Dusk / night / rain | Dusk has a warm orange horizon and water response; night is dim blue rather than a bright cyan field; rain has overcast cloud light and dense vanilla streaks. | Distinct time/weather rendering retained. No solar disk is visible in the dusk pose, and no broad sunlight-quality conclusion follows. |
| Underwater | Dark blue haze, faint bottom/kelp and square vanilla particles remain, qualitatively similar to 0.4. | No catastrophic underwater regression seen; not measured real-water visibility. |
| Upward near / deep / tilt | All retain a curved Snell-window-like sky opening with dark surrounding water, rather than the old rectangular viewport fallback. Deep is visibly bluer; the tilted boundary remains curved. | The prior upward-sky fix is retained at these three guarded poses; not complete angular/TIR validation from images. |
| Moving-view | Open-water reflections remain, with cyan/blue stepped bottom patches and sharp band transitions at the right. | Another observed quality gap; one rotating-scene still proves no temporal smoothness. |
| Boat-contact | Mounted boat geometry and surrounding water render; the bow obstructs foreground water and the wake behind is outside this view. | Bridge contact is exercised, not a demonstrated realistic wake or smooth boat motion. |
| Cave-water | Muted gray-blue water remains in narrow lush-cave channels beside dark stone and locally lit foliage. No obvious bright daytime sky leaks into the shown sheltered water. White-gray water/plant edges remain. | Limited cave compatibility retained, not all-cave lighting or realistic foam validation. |
| Glass-layers | All three temporary transparent glass slabs show blue borders with ocean/clouds visible behind. | No obvious depth/fallback catastrophe here; not a physical multilayer glass-energy/refraction test. |
| Nether / End | Red/brown Nether terrain, fire/lava and dark purple End sky/terrain remain; neither shows Earth daytime clouds. | Dimension fallbacks retained in these views; no physical Earth-atmosphere claim for those dimensions. |

No new obvious full-frame missing-water, rectangular upward sky or Earth-sky-in-non-Earth regression was found in the reviewed stills. This does **not** establish that all rendering regressions are absent. No 0.5 temporal clip was reviewed or accepted; the 0.4 sampled motion findings, including the boat-relative jump caveat, are not new 0.5 motion evidence.

## Incident-Sun source review and numerical limits

The current ZIP entries byte-match these inspected production sources:

| Source | SHA-256 |
|---|---|
| `shaders/lib/water.glsl` | `e9e6ac73ca6c451907e8f515913898b000e494c55947cd5e2f44d05db3d65b39` |
| `shaders/composite.fsh` | `3d12aea1221fb2773db71c5408bdce8c2b29de5bae98f2584577f785434cf6c1` |
| `shaders/gbuffers_water.fsh` | `ff410013c1f9242479c8983d99b062e2779cb9237984a93ffbac5c0aad1c62f6` |
| `shaders/lib/lighting.glsl` | `16cf5a6c9b78b70b7cef735a58628742dffe8249fdba8443ede4a2a088ab2e34` |

The helper at `water.glsl:26–34` now multiplies admitted normal-interface flux `(1-Fresnel)` by Beer extinction over the horizontal-surface Snell beam path. C8 remains the raw air-lit receiver Sun attribution. Underwater `composite.fsh:36–52` uses paired raw depth/C8, replaces only that Sun contribution before the existing single outgoing-eye transmission/scatter operation. Above-water `gbuffers_water.fsh:241–261` applies the same helper only to a confirmed upper-surface receiver, then its outgoing view leg; confidence still blends separately attenuated hit/proxy radiances. Unknown original-UV proxies do not acquire guessed Sun-leg corrections.

The final separately produced [native full-check log](../../reports/2026-10-02-v0.5.0/native/water-v0.5-both-sides-full-check.log), SHA `84d5cf1cfbd15f36f059e0d5f8d3b5731972cc8743dfcac22c35dcc324a27da8`, reports all eleven production program pairs and its existing controls PASS. This reviewer read the log, **did not run GPU tests**. At fixed one-metre eye leg, adding two metres incident depth gives observed RGB ratios `0.527292 / 0.843665 / 0.932394`, matching the Beer reference. Absolute normal-entry reflected fraction `0.0203732` is tested too. Above-water paired real-bed response gives `0.278069 / 0.711784 / 0.869316` versus independent two-leg references `0.278037 / 0.711770 / 0.869358`. The previous underwater directional sky/TIR, zero-source, source attribution, depth pairing, opaque-foreground rejection and original smooth-bed continuity bracket remain PASS in that log.

Those are bounded transport/provenance improvements, not photographic calibration or proof that every real-bank transition is continuous. The horizontal local water plane does not establish actual water membership along every solar path. Raw C8 still contains air-direction receiver-normal/shadow effects; arbitrary submerged normals, bent-ray shadows, bank-side exits and dry pockets are not reconstructed. The helper returns identity at nonpositive depth or Sun below the horizon, so the native positive-depth slice is not a proof of all boundary behavior. Local mean-plane depth, approximate RGB extinction/scattering and unknown-ray proxies remain. The original [Beer-only incident review](codex-v0.5-incident-review.md) is historical first-slice evidence, including its then-failing Fresnel test, not a statement that the final candidate lacks this subsequently added Fresnel/both-sides work.

Remaining visual priorities are the unresolved optical-normal/geometric-surface coupling, reflection source/validity handoff, and real stepped-bank refraction/proxy rejection. The broad cyan/serrated appearance is the observable repro; its precise source cannot be assigned from a still or solved merely by calling the native flat-bed test GREEN.

## Integrity, timing and cleanup boundary

Independent checks pass all **16 bounded 1600×900 PNGs** (chunk CRC/order, complete IEND/zlib/full scanlines) and **24,701 finite positive CSV render-tail intervals**. CSV frame indices, ns/ms consistency and all stored metric fields recompute within the existing tolerance. Every scene's world/pack identity, active/no-fallback status, actual window/framebuffer, local-player camera identity, HEAD lock and actual camera/player angles agree with its recorded expectations; all capture-time focus fields are true. Nether/End dimensions are correct and the other fourteen are Overworld. The three upward scenes also pass the existing first-person/eye/submersion/fluid-surface/time validators.

`tools/report.py::load_run` intentionally requires 2560×1440, so this is an explicit read-only **1600×900 artifact audit**, not a claimed pass of that unchanged 1440p report boundary. The complete marker matches all sixteen scenes, has no abort record and says `fixture_cleanup_complete=true`.

| Scene | Raw intervals | Observed mean FPS | Worst interval ms |
|---|---:|---:|---:|
| coast-day | 1,104 | 220.80 | 7.797333 |
| river-day | 1,126 | 225.20 | 8.439102 |
| ocean-day | 1,141 | 228.26 | 7.996789 |
| ocean-dusk | 1,109 | 221.98 | 7.983395 |
| ocean-night | 1,195 | 239.11 | 6.527523 |
| ocean-rain | 1,037 | 207.49 | 7.781054 |
| underwater | 1,252 | 250.58 | 6.648039 |
| underwater-up-near | 1,492 | 298.57 | 7.282794 |
| underwater-up-deep | 1,474 | 294.89 | 6.391777 |
| underwater-up-tilt | 1,493 | 298.68 | 6.736125 |
| moving-view | 1,120 | 224.08 | 7.086105 |
| boat-contact | 1,127 | 225.46 | 7.894507 |
| cave-water | 1,295 | 259.17 | 6.502616 |
| glass-layers | 1,136 | 227.31 | 11.434213 |
| nether-view | 4,233 | 846.74 | 3.370217 |
| end-view | 3,367 | 673.57 | 7.038184 |

No recorded interval exceeds `1000/60` ms in these short samples; the worst is `11.434213` ms in glass-layers. These are wall-clock render-loop observations, not GPU-only throughput, a sustained FPS-floor guarantee, controlled repeat averages or shader-performance causality. Recorded frame-limit **260** must not be called verified unlimited; some measured scene rates exceed it, and this audit does not explain that behavior. Different scene workloads should not be pooled into a meaningful gameplay rate.

Boat contact samples all report an active bridge and one contact; maximum force reaches `8.0`. The driver is **server-command translation at 6 m/s, 20 Hz**, not vanilla rowing. That validates nonvacuous inputs, not physical wake fidelity. Coast contacts/turtles are a separate uncontrolled disturbance.

The root-exported [`fixture-after-test-stop.json`](../../reports/2026-10-02-v0.5.0/fixture-after-test-stop.json) records a saved-Anvil read-only audit of the earlier 390 reserved opaque/air cells: all exact AIR, cleanup/no-pending-journal true. This reviewer read that evidence but did not rerun a live-world audit. Those cells are separate from this run's three temporary glass slabs; the complete marker is the available runtime cleanup evidence for the glass scene. This visual audit does not inspect or modify the ordinary user world/settings.

## Reviewed candidate PNG SHA-256

Paths are relative to `reports/2026-10-02-v0.5.0/real-view/`; hashes identify original captures, not edited illustrations.

| PNG | SHA-256 |
|---|---|
| `coast-day.png` | `659c9f63a1a7450b8c630d2ddf2eaac3b7882573f04cc19d15b811b2cdbb8fb4` |
| `river-day.png` | `7658a90d4aa5d83d603c48c04be7127e8cda248495c2615ff84b3f65089ceb3e` |
| `ocean-day.png` | `e94c34646d293d565bc59634ac14a8b265736223bee06a3ca772f7b8a78af7eb` |
| `ocean-dusk.png` | `84e91de4fb641af2292e332c5a44fa0e2f47fd68bc1293b3c134336d1022cd75` |
| `ocean-night.png` | `e9df17203274343dcb653e5daad93c7dcd46408e95f6233eb56a9f03652409fb` |
| `ocean-rain.png` | `c7ec4d0d6c9c8621333100306cbd2ac4b6368dcc8a85b046f01f8a775db8af15` |
| `underwater.png` | `46947c4ba283e0db012f2276feea91050ec4980b02a6b4305bf454e05d4e9aba` |
| `underwater-up-near.png` | `dc17444c15727e3fa6791301554dac8ffa729093ce2cc63dea2d7cc9a8908eff` |
| `underwater-up-deep.png` | `47e1baaba1649b4c7c30e34f77e602a0d6a2cc3bd1089451d70c71267e4b199b` |
| `underwater-up-tilt.png` | `c22227491ae9fdbae9086d6d27398ecdbf52bca0b94322eb1d16ed7c3dd381a2` |
| `moving-view.png` | `04572c2c08e3922195d8f4881069ec4bc195f551805c9a908b55bee069cacbbe` |
| `boat-contact.png` | `41097974ec6a20903cb235c257b4d038ddaedd5ae55624dc07dbe0c8334496f9` |
| `cave-water.png` | `e86dcda9573225b36fc5a55a9e1f9f38088ef854dff960c468ad830d4b3f924d` |
| `glass-layers.png` | `5713474dba9dfe2c03fda90370d030d3e9081d9627508c49e8d7af7c21edd17d` |
| `nether-view.png` | `4c5ef332e6e1285b47d232108bdbffb07ece0aa3f95fd0d12d15d4eea86ec12a` |
| `end-view.png` | `392fe716b47448862e31034f83aa00c31d68e4deaad7381618c7bc512f97bb6f` |
