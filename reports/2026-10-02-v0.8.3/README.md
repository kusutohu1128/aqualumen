# 0.8.3 development checkpoint: direct receiver radiance on water exit

The known direct-Sun receiver component now includes water-to-air directional
radiance conversion. This is a qualified original-main optical correction,
**not completion of natural-water appearance or the full goal**. Six actual
Minecraft views and terrain/water C7 prepared-input observations are now recorded.
Ordinary0.6/physics0.2 is reopened paused; this candidate is not promoted.

## Reproduced defect and bounded correction

The declared C8 source is dry Lambertian radiance `rho*E_air/pi`. Incoming
Fresnel/Beer changes bed irradiance without an index-squared multiplier.
The separately exiting directional radiance receives `(1/1.333)^2`, consistent
with the [PBRT dielectric model](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF#sec:non-symmetric-scattering).
Applying those units to this known component is a model inference; B/ambient,
proxy, scattering and reverse underwater air-sky entry are not calibrated here.

Only the existing above-water upper-interface, confirmed opaque receiver,
Earth direct-Sun branch changes. Algebra is `behind += D*(I*focus*q - 1)`:
remove the complete old dry D, then add the transported direct component.
No global dimming/desaturation or extinction-coefficient change is used.
C8=0, unknown proxy, reflection, scatter and underwater paths are unchanged.

## Genuine original-main RED / GREEN

Actual RTX3080Ti/NVIDIA GL4.6 runs original water VS/FS main with only public
WAVE_HEIGHT0/SHORE_FOAM0. Fixed65x65 centre32,32, phase120, zenith Sun,
camera worldY65, interfaceY63, visible closed horizontal bedY61.5.
Independent first-bed/visibility and four pixel-corner Snell footprints qualify
geometry before RGB algebra; original VS renders explicit planar triangles.
All valid64x64 bathymetry, inactive ripples, confidence1, focus1, normal up,
vertical transmitted direction and each actual1.5m path are checked.

Pairs C4=B+D8/C8=D8 and C4=B/C8=0 use actual declared16F D8 readback, while
C0/C4 query32F. DeltaC4-D8 residual is separately propagated. Positive source,
zero-source, positively read-back off-source reflection tag, whole-image original
repeat and passive-store neutrality pass before judging absolute source gain.
Removing observer stores recovers byte-identical public-option main. Full C0
magnitude, storage half-ULPs, declared gamma512, Fresnel, supplied-depth and
pixel-path allowances form the numerical bound; it is not a universal driver
transcendental-accuracy theorem or physical-parameter calibration.

| RGB channel | Old gain | Corrected gain | Independent expected |
| --- | --- | --- | --- |
| Red | 0.07347107 | 0.04134750 | 0.04134874 |
| Green | 0.11156845 | 0.06278992 | 0.06278818 |
| Blue | 0.08638000 | 0.04861069 | 0.04861318 |

Old ratios are1.776864–1.776902, exceeding unchanged full bounds0.00267–0.00284.
Two old-source runs reproduce byte-identical response CSVs. Corrected ratios
are0.999949–1.000028. The formal isolated repeat reproduces the first GREEN CSV.
The first GREEN and first full-suite launch occurred without awaiting terminal
confirmation, so overlap was possible; both passed but neither supplies timing
evidence. Both were then rerun with explicit terminal sequencing. The serial
full native suite, retained local-cloud/C8 and nonzero-wave first-bed tests pass.
All GPU jobs are terminal before any new Minecraft validation.

Directly readable [old response](native/red-response.csv),
[corrected response](native/green-response.csv),
[geometry qualification](native/geometry-qualification.csv),
[serial GREEN log](native/green-serialized.log) and
[serial retained suite](native/full-native-serialized.log) accompany the
[full raw evidence archive](native/radiance-evidence.tgz).

## Candidate identity and unmet requirements

ZIP SHA256 `644862e623cffe13d6a8cec9ab588cd081233c67100c3b4dac6ab3476b5a2caf`.
Water FS `c8cdbde6bc15fbf7dab3b59efd6f2897202eb2d5a1c0aee6bf71890b5f7e4ced`.
Radiance harness `3a1082ba9c9b157e3af6919b983127b05268d0202c5ede082e156111c9b7926d`.
Old0.8.2 ZIP is unchanged. Actual Minecraft FPS/appearance are not inferred from
native runs. The achromatic exit factor alone cannot certify cyan hue, shore
serration, temporal waves/wakes, cloud shape or full angular/medium transport.
Implementation/review are Codex work, not a claimed Claude invocation.

## Actual Minecraft views and frame observations

The [completed six-view run](captures/v083-radiance-smoke-20261002-1610/run.json)
activates the exact0.8.3 ZIP without fallback on Minecraft1.21.1/Iris1.8.8/
Sodium0.6.9, physics0.3.0 and benchmark0.3.8. Only the approved disposable
V2 world UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`, seed308060, is automated.
All six views are focused1600x900, cap120/VSyncOFF, 12render/6sim,20s warmup/5s
sample. Actual Minecraft uses NVIDIA GL3.2, not native GL4.6.

The [CPU raw-data audit](smoke-audit.json) verifies6 bounded PNGs and independently
recomputes3009 positive integer-ns intervals totalling29,968,964,690ns.
The general1440p `tools.report.load_run` rejects900p as designed; it was not
weakened or fed altered metadata. Existing public PNG/head-pose validators and
independent raw ns arithmetic verify this explicitly limited900p checkpoint.

| Scene | Mean FPS | 1% low FPS | Worst ms |
| --- | ---: | ---: | ---: |
| Coast | 91.978 | 71.154 | 15.038 |
| River | 88.808 | 71.967 | 13.992 |
| Ocean | 66.145 | 53.913 | 18.986 |
| Underwater up near | 118.420 | 114.180 | 9.334 |
| Underwater up deep | 118.524 | 117.160 | 8.656 |
| Underwater up tilt | 118.491 | 117.525 | 8.659 |

Ocean has46 intervals slower than16.667ms. No1440p,60FPS floor, controlled
timing A/B or motion guarantee follows. Root viewed all6 original images:
[visual audit](VISUAL-AUDIT.md). Cyan/mint shallows, sharp dark bands and artificial
clouds remain. All3 underwater-up views show no old inner rectangle/double map,
but strong round curvature/dark exterior remain unaccepted. Near/tilt measured
eye depth0.499889308m, deep3.249889308m; actual local camera/head is submerged
WATER, first-person, daytime6000, with no terrain placement.

## Real C7 prepared input, outside timed sampling

Two one-shot [observations](observations/audit.json) run after the completed
six-view measurement, through actual SodiumShader.setupState TAIL. In water
program421 C7 is active sampler2D/unit4 and C6/unit3; terrain program415 uses
C7/unit3 and C6/unit1. Dynamic units are queried, not guessed from buffer indices.
Both name-to-binding chains identify C7 texture60/target7-alt, C6 texture58/
target6-alt, actualRGBA16F1024x512/base0. Both C7(0,511) read
RGB(0.93017578125,0.875,0.7490234375)/alpha1; reserved neighbour(1,511) isRGB0/alpha1.
All11 caller-state fields match before/after and both observers report available/
scopeAuthorized/stateRestored. This closes the earlier allocation-only evidence
gap for the named prepared input. It does **not** prove a specific fragment fetch
or same-frame producer freshness; those flags explicitly remain false.

The [frozen0.3.8 observer source/JAR/CPU packet](observer/README.md) retains old
0.3.7 unchanged. Its historical CPU-freeze `actualIrisExecutionVerified=false`
is not rewritten; the separate later observations provide the real execution
checkpoint. No observer readback is included in FPS samples.

## Lifecycle and ordinary handoff

TEST Save/Quit reaches player disconnect and the native `Saving world` screen
but again stalls. The freshly revalidated own TEST Java2946763 and its launcher
2946639 alone receive TERM at07:19:40Z; session60422 exits143 and both processes
are absent. This is not a clean exit or a shutdown-defect fix.
Saved Anvil AIR/no-journal audits before launch, before quit/stop and after exit
all pass for390 exact reserved cells, not whole-world/entity integrity.

Original options/Iris/benchmark properties are byte-restored **before relaunch**,
ordinary saved files matched the fresh post-user-play backup at that prelaunch
point, and no ordinary world is restored or automated. Candidate physics/benchmark/marker/C7 request
are recoverably disabled. See [prelaunch ledger](lifecycle/restoration-before-normal-launch.json).

The normal user/account/world is subsequently reopened with0.6/physics0.2,
no benchmark and no shader fallback, then paused using the actual native menu.
[Handoff ledger](lifecycle/ordinary-paused-handoff.json) and
[native F2 image](lifecycle/normal-restored-paused-native-f2.png) record that point.
Iris naturally regenerates its timestamp comment after launch; semantically
unchanged settings are not misreported as current whole-file byte equality.
Ordinary autosaves after reopening are natural game writes, not world restoration.
Both TEST and ordinary logs retain an OpenAL-device startup error (sound/music
turned off); TEST also has an offline auth401 warning. These are not shader
fallbacks, but no audio/auth repair or all-feature runtime-health claim is made.

All desired natural-shore/cloud/motion/broad-physical requirements remain open.
Next distinguish the correct flat Snell angular map from wave-rim warp and
missing offscreen underwater reflection; do not cosmetically shrink the physical
window or count this bounded radiance correction as full-goal completion.
