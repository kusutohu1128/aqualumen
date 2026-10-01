# Solar disk / direct-beam radiometry plan

Design checkpoint: 2026-10-01 21:15 UTC (2026-10-02 06:15 JST). This is a read-only source review plus CPU mathematics, not a shader change or a fresh GPU result. All proposed runtime tests below are **pending**. The ordinary game and exclusive GPU work were not touched. The overall water/sunlight goal remains active.

## Finding and decision

The current analytic disk and direct illumination share the same observer atmosphere/cloud transmission cache, but they do **not** represent the same energy. For a sharp disk of the implemented angular radius, integrating the current disk gives only `0.00135857195` of the direct beam: about **0.136%, or a 736.067-fold deficit**. The actual derivative-smoothed disk has a projection-dependent integral, so this sharp-support number is not an exact measurement of a Minecraft frame.

A correct unattenuated red disk would need approximately `264984` scene-radiance units, exceeding the actual `RGBA16F` storage range. Do not change the disk multiplier alone. First record one failing regression through the production terrain/deferred mains; then make a bounded disk-energy, coverage, and storage-range change. No solar fix is implemented or declared complete here.

The diagnose skill shaped this plan: a production-main falsifiable RED comes before the proposed fix; helper-formula agreement alone is not the acceptance seam.

## Actual transport and provenance

`SOLAR = (18, 17.6, 17)` is best interpreted as perpendicular solar-beam irradiance in arbitrary linear-RGB scene units, not measured W/m². Terrain divides it by π for a Lambertian receiver; atmosphere multiplies it by normalized scattering phase functions. Radiance and irradiance are distinct quantities: `E(n) = ∫ L(ω) max(n·ω, 0) dω`. [PBRT radiometric integrals](https://pbr-book.org/4ed/Radiometry%2C_Spectra%2C_and_Color/Working_with_Radiometric_Integrals), [PBRT radiometry](https://www.pbr-book.org/4ed/Radiometry%2C_Spectra%2C_and_Color/Radiometry).

Let `Tair` be clear atmospheric RGB transmission, `Tcloud` the observer-to-Sun cloud-column transmission, and `W = 1 − 0.85·rainStrength` the extra legacy weather scalar.

| Actual source / consumer | Quantity and factors |
| --- | --- |
| `prepare.fsh`, reserved final-row C7 pixel | Dimensionless `Tair`, computed by `solarTransmission(sun, max(cameraY−63, 2))`. Planet occlusion and 16-step optical depth are included. |
| `prepare.fsh`, reserved final-row C6 pixel | Dimensionless `Tair·Tcloud`. Cloud-column extinction already depends on rain through density/coverage/extinction. The cache returns before the normal LUT rain-color mixing. |
| Normal C7 / C6 LUT rows | Clear / clouded directional radiance, respectively. Neither includes an analytic Sun/Moon disk. Rain desaturation is a separate approximate color operation on these rows. |
| `lighting.glsl` → terrain C5 → deferred C8 | Sun-only receiver radiance `albedo·SOLAR·Tair·Tcloud·W·max(n·sun,0)·shadow·skylight / π`. C8 is a matched immutable receiver component, not total RGB. |
| `atmosphere.glsl::sunDisk` | `SOLAR·Tair·Tcloud·20·qδ(angle)`. No `W`; this expression is treated as directional radiance by the sky renderer. |
| `illumination.glsl::waterIncidentIrradiance` | Horizontal admitted-beam approximation `SOLAR·Tair·Tcloud·W·max(sunY,0)·visibility·0.98`, plus diffuse/Moon/block illumination. `0.98` is a normal-incidence approximation, not exact angular Fresnel. |
| `gbuffers_water.fsh`, analytic direct glint | `SOLAR·Tair·Tcloud·W·visibility·sunSpecular(...)`. `sunSpecular` already contains BRDF times `n·l`; supplying beam irradiance is appropriate. Its roughness floor is a finite-disk approximation, not an area-light convolution. |
| `clouds.glsl::addCloudLayer` | Cloud source uses `SOLAR·solarTransmission(sun, cloud mid-altitude)` and in-cloud light optical depth. This is not the observer C6 cache and should not acquire another blanket observer-cloud attenuation. Multiple scattering/aerial coupling remain approximations. |

The first test compares the closed model's shared observer cache; it does not establish that one camera-column transmission is physically valid at every terrain receiver.

Reflection call sites were checked. `filteredWaterSky` samples **only** the disk-free C6 LUT; the direct GGX Sun is added separately. `reflectionTrace` accepts opaque depth hits, not sky-depth hits. `environmentSkyRadiance = sampleSky + sunDisk + moonDisk` is used for the camera background and refracted infinite sky. This review does **not** assert analytic-disk double counting in the reflected-sky fallback.

## Angular-support calculation

Implemented radius `α = 0.00465 rad = 0.266425375°` (diameter `0.532850749°`). For constant disk radiance and a receiver perpendicular to the Sun axis:

```
Ωdisk = 2π(1 − cos α)       = 6.79289647526e−5 sr
J0    = ∫disk cos θ dΩ     = π sin² α = 6.79285975548e−5 projected sr
Ecurrent / Ebeam           = 20 J0   = 0.00135857195110
Ebeam / Ecurrent           = 736.067014481
Lcorrect / (SOLAR·T)       = 1 / J0  = 14721.3402896
```

At `T=(1,1,1)`, the sharp current disk integrates to RGB `(0.0244542951, 0.0239108663, 0.0230957232)` rather than `(18,17.6,17)`. A normalized sharp disk has RGB radiance `(264984.125, 259095.589, 250262.785)`.

Actual source uses `δ=max(fwidth(angle), 0.0001)` and `qδ=1−smoothstep(α−δ, α+δ, θ)`. For a **fixed** δ≤α, the appropriate integral is `Jδ=2π∫₀^(α+δ) qδ(θ) cosθ sinθ dθ`, not Ω alone. Double-precision Simpson integration with 100000 intervals gives:

| Fixed δ (rad) | Jδ (projected sr) | Current E / beam E | Jδ / J0 |
| --- | ---: | ---: | ---: |
| 0.0001 | 6.79348804683e−5 | 0.00135869760937 | 1.000092493 |
| 0.001 | 6.85568888243e−5 | 0.00137113777649 | 1.009249290 |
| 0.002 | 7.04417615558e−5 | 0.00140883523112 | 1.036997142 |
| 0.004 | 7.79812363257e−5 | 0.00155962472651 | 1.147988316 |

For small angles, `Jδ≈π(α²+δ²/5)`. There is no compensating normalization in the current smoothstep. On a real projection δ varies with position and azimuth; fixed-δ CPU integrals are source-derived predictions, not measured framebuffer integrals. Merely replacing `20` by `1/J0` leaves this antialiasing energy drift.

Rain is another independently falsifiable inconsistency: with the same synthetic cache, disk energy lacks `W` while beam energy includes it. At rain=1, their ratio changes by `1/0.15=6.6667`, independently of the cloud-cache rain response. This does not prove that the legacy weather scalar itself is physically calibrated.

## One first production-main RED — pending

Proposed name: `productionSolarBeamCoherenceProbe`, extending the existing `tools/glcheck.cpp::terrainSunSnapshotProbe` MRT seam. **The probe has not been written or executed.** It must link the actual `gbuffers_terrain.vsh/fsh` and actual `deferred.vsh/fsh`; no copied Sun body, diagnostic replacement shader, overridden `SOLAR`, or helper-only pass is the acceptance test.

1. Use Overworld dimension, Sun at zenith, rain=0, white albedo, receiver normal toward Sun, full skylight and unoccluded shadow. Supply C6 with black radiance rows and final-row solar-cache RGB `(1,1,1)`. This intentionally isolates consumer transport, not natural atmosphere/cloud generation.
2. Render real terrain C0/C5 and run real deferred with opaque depth. Infer `Eterrain = π·C8/albedo`; validate it against actual `SOLAR` per channel. Do not use total C0, because ambient/Moon/block components would contaminate the measurement.
3. In a separate draw, run real deferred's background branch with depthtex1=1, the same C6 cache, black other inputs, and a Sun-centered perspective view. Start with 512×512 and 2° vertical FOV so the entire disk and smoothing support fit in the viewport and the edge derivative is below the δ floor. Do not pass through exposure, tonemapping, final filtering, water, or clouds.
4. Read raw C0 and C4 and integrate `Esky = Σ Li·max(ray_i·sun,0)·Ωpixel_i`. Derive rays from the actual projection/inverse-view matrices. Independently compute each pixel's solid angle from its four unit corner rays; triangulate the spherical quad using `2 atan2(|a·(b×c)|, 1+a·b+b·c+c·a)`. Check numerical convergence rather than assuming equal pixel solid angles. A central-ray cosine is the convergent pixel approximation, not an exact within-pixel cosine integral.
5. Gate every RGB channel on `0.98 ≤ Esky/Eterrain ≤ 1.02`. Require finite C0/C4, matching sky snapshots, a valid positive terrain beam, fully initialized attachments, and no GL errors. Current CPU source mathematics predicts approximately `0.0013587`, so the current production mains should fail the unity gate decisively. **This prediction is not a recorded GPU RED.**
6. Include the zero-cache control: both analytic Sun and C8 must vanish. Record actual texture internal formats. Run the current declared RGBA16F setup first; existing MRT fixtures allocate RGBA32F and therefore do not by themselves validate Iris's half-float storage behavior.

Ranked, falsifiable explanations before execution: (1) the arbitrary `20` lacks the beam-to-disk angular conversion; (2) smoothstep broadening adds projection-dependent energy; (3) direct-only weather scaling breaks common-source coherence; (4) a naive calibrated disk cannot fit the current storage. The first real-main unity measurement tests (1) without first entangling water or clouds.

After recording that RED, reuse the same probe for colored cache values, rain=1, wide FOV at 900/1440 pixel heights, off-center disks with full support visible, and convergence checks. A separate later real-prepare control should verify `T6 = T7·Tcloud` at fixed camera/time and show that each downstream consumer attenuates its common beam exactly once. Synthetic-cache success alone does not validate cloud physics or real Iris rendering. All these follow-ups are **pending**.

## Bounded change after RED — proposed, not implemented

Preserve `SOLAR`, disk radius, atmospheric scattering, receiver-Sun isolation, and existing water incident/outgoing Beer attenuation. Make observer direct-beam units explicit: `Eperp = SOLAR·cachedT6·W`, applied once by each observer direct consumer; derive disk radiance from that same beam, `Ldisk = Eperp/J0`. Keep cloud-altitude scattering inputs separate. Use energy-preserving angular/pixel coverage, not an unnormalized smoothstep halo; the production-main integral remains the arbiter. The exact coverage implementation must be measured for convergence and cost before selection.

Promote only full-resolution **C0 and C4 to RGBA32F before increasing disk radiance**. Current `prepare.fsh` declares both RGBA16F, and deferred writes the analytic disk into both. Leave C5/C8 receiver diffuse Sun and C6/C7 LUT/cache storage unchanged unless separate range evidence requires otherwise. Query actual native/Iris formats when testing; a source declaration or an already-32F fixture is not sufficient confirmation.

Binary16's largest finite value is `(2−2⁻¹⁰)·2¹⁵ = 65504`. The normalized clear red disk is `4.0453` times this maximum; even red transmission above `0.2471997` exceeds the range. A 16F store cannot preserve that value. Exact clipping/infinity/conversion behavior is untested here; no fresh NaN claim is made. Exposure in `final.fsh` is downstream of HDR storage and cannot recover lost values. [Khronos float formats](https://wikis.khronos.org/opengl/Small_Float_Formats).

Iris uses two storage images per colortex target. Assuming both promoted full-resolution targets retain both images, extra storage is `2 targets × 2 images × 8 extra bytes/pixel`: **112.5 MiB at 2560×1440**, or **43.945 MiB at 1600×900**. Actual allocation/bandwidth and 3080 Ti frame time must be checked in a fresh controlled Iris run; this is not a 60 FPS assurance. [Iris colortex buffers](https://shaders.properties/current/reference/buffers/colortex/).

Keep a 16F negative-range control beside the corrected 32F test. Require the new calibrated sky to remain finite, preserve integrated energy and channel ratios, and survive C0→C4 transport. A global pre-exposure alternative would require coordinated scaling of all solar/Moon/block/floor/cloud sources and inverse exposure; scaling only the Sun would introduce a different inconsistency and is outside this bounded first change.

## Refraction boundary: do not confuse radiance with beam power

`waterSunBeamTransmission` already models admitted collimated power as `(1−Fsun)·Beer(depth/cosθwater)` separately from the receiver-to-eye leg. Do **not** multiply this beam irradiance by η². At a dielectric interface, radiance changes with the angular compression while transmitted power remains Fresnel-admitted; that Jacobian is a different quantity. [PBRT dielectric radiance scaling](https://www.pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF).

For air→water at normal incidence, η=1.333 gives η²=1.776889, F=0.020373188, admitted power=0.979626812, and physical transmitted radiance ratio `(1−F)η²=1.740688107`. The refracted disk's projected angular support shrinks by `1/η²=0.562781356`, canceling the radiance gain in its power integral. A Fresnel-only radiance mix instead predicts an integrated ratio about `0.551315705`.

The current underwater infinite-sky path calls `environmentSkyRadiance` at the refracted direction and mixes with Fresnel, without an explicit medium-radiance η² factor. This is a separate candidate boundary regression, **not** a reason to increase the already-admitted receiver beam or undo established one-time Beer/Fresnel corrections. A later real water-main test must isolate the air-to-water disk, its compressed angular support, and power conservation before any change. It is pending and excluded from the first air-side RED/fix.

## Exact reviewed source checkpoint

SHA256 read at the checkpoint above; future edits require a new source identity before interpreting test evidence. These are source hashes, not an installed-pack or completed-fix claim.

| Path | SHA256 |
| --- | --- |
| `shaders/lib/atmosphere.glsl` | `9fb86309bdd082a6637ccab71fd34549b9da9a548b6148893c2e40681b1e3655` |
| `shaders/lib/illumination.glsl` | `b32770d63a7e1399b18ff8a526c4115d13116058f77fd4a1464af83452460c95` |
| `shaders/lib/lighting.glsl` | `16cf5a6c9b78b70b7cef735a58628742dffe8249fdba8443ede4a2a088ab2e34` |
| `shaders/lib/water.glsl` | `e9e6ac73ca6c451907e8f515913898b000e494c55947cd5e2f44d05db3d65b39` |
| `shaders/lib/clouds.glsl` | `5a3d6a94a623118f6a675874a69d8251b4428d60c5b57cc44b3d2c9c297957b3` |
| `shaders/lib/settings.glsl` | `4eac3729dc8cb999168f720d7cba6525e588cb99757062ab1b57e9f00322445d` |
| `shaders/prepare.fsh` | `a4919f0cf43f77a736b3b92b386c4b7625fc06f1df5d9e07f5160cfc29fb084e` |
| `shaders/deferred.fsh` | `e6f799d997e7e5c08d07c54cb954fd1c6e5d86bc93471eb6ce09361fe3b2ada9` |
| `shaders/gbuffers_water.fsh` | `ff410013c1f9242479c8983d99b062e2779cb9237984a93ffbac5c0aad1c62f6` |
| `shaders/composite.fsh` | `3d12aea1221fb2773db71c5408bdce8c2b29de5bae98f2584577f785434cf6c1` |
| `shaders/final.fsh` | `43f44c9272273542be0e6fcf5448007cf2c01fd7afca01ed82fa4fcab5cdbfaf` |
| `shaders/shaders.properties` | `49d777fbdd776ad6e535e237966b739cc6803e4df7bbd0b7ab1563e4e8b9dc76` |

Settings reviewed: WATER_ROUGHNESS default 0.075, WATER_CLARITY 1, EXPOSURE 1, NIGHT_EXPOSURE 16; there is no solar-energy/disk-size option. Vanilla Sun rendering is disabled. Final exposure/tonemapping/filtering must remain outside radiometric measurement.

Acceptance remains open: record production-main RED; implement only the bounded change; obtain production-main GREEN with format/coverage/weather controls; then validate actual Iris visuals and record fresh 1440p frame timings honestly. The user relaxed the original60FPS floor: it is neither a release acceptance gate nor a guarantee. This document alone completes only the design subtask.
