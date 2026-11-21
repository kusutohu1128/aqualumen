# Aqualumen 0.6.0 shore-search and solar-radiometry checkpoint

2026-10-02 JST. Built, installed and ordinary-runtime verified experimental
checkpoint. **The full realistic water and sunlight goal remains active.**
Implementation and independent reviews are Codex work; no new Claude invocation
or full visual-completion claim is made. Earlier releases and evidence remain.

## Artifact and preserved provenance

Built/installed/selected/runtime-active `Aqualumen-0.6.0.zip` SHA-256:
`6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`.
The retained 0.5 ZIP is unchanged:
`88ff19eed363ff3d25287b3873ed7c0ac7b2ca654074e0365d510fedd07c859d`.
Both distribution hashes were re-read during this documentation update; no
rebuild was performed here. Physics 0.2.0 is unchanged. Benchmark 0.3.4 is a
development observer/recorder, not a required normal-play Mod.

[Final source and validation-tool archive](native/final-source-and-validation-tools.tar.gz)
retains shaders, license, build target, Makefile, native probes and observer/
recorder/test sources. [Historical causal artifacts](native/shore-causal-artifacts.tar.gz)
and [final-current shore artifacts](native/shore-final-current-artifacts.tar.gz)
preserve raw responses and expanded inputs. The historical GREEN tree contains
a copied, stale `red.log`; the matching first-GREEN execution is the separate
[stdout](native/shore-visible-bed-first-green.log). Filenames do not establish
source/log correspondence. The initial causal export's CPU palette-reporting
error and corrected export are retained separately. See the
[evidence plan and final follow-up](../../docs/reviews/codex-v0.6-evidence-plan.md)
and [checkpoint detail](WORK-IN-PROGRESS.md) for these scope limitations.

## Bounded production-main corrections

The shore regression keeps one physically visible receiver across a
48-micrometre boundary perturbation and varies only its tagged green radiance.
The old above-water fixed-point trace skips an intermediate depth cell and
loses a positive response (`0.100883 → 0`). The new sampled-crossing search
retains responses `0.100884780288/0.100881353021`, differing `3.42727e-6` within
the unchanged independent physical/one-depth-pixel bound `0.001669252223`.
Existing viewport, surface, foreground-bank and final-residual guards remain;
underwater/vertical-face iteration policy is unchanged. Positive reflection/
bed controls and full-image observation-neutrality pass. This is a causal
receiver-loss correction, not proof that every natural shoreline is fixed.
See the [independent causal review](../../docs/reviews/codex-shore-causal-review.md).

Solar tests use actual terrain/deferred mains, a controlled atmosphere cache
and black ordinary sky, then independently integrate raw sky radiance with
spherical corner-ray solid angles and cosine weights against the terrain beam.
Zero/positive source, actual format, finite output, C0/C4 snapshot and independent
quadrature checks guard the unchanged per-channel ±2% coherence gate.

| Increment | Preserved failure | Preserved passing result |
| --- | --- | --- |
| Clear disk/beam energy | [Old source](native/solar-radiometry-v0.5-red.log): ratios about 0.001357 | [First GREEN](native/solar-radiometry-first-green.log): 1.000123–1.000527 |
| Existing rain convention | [Rain-only RED](native/solar-radiometry-weather-red.log): about 6.667 | [Rain GREEN](native/solar-radiometry-weather-green.log): 1.000007–1.000205 |
| Normal-view coverage | No fabricated RED is claimed | [1600×900](native/solar-ordinary-fov-first.log), [1440p](native/solar-1440p-first.log), [0.37-pixel phase](native/solar-1440p-phase-first.log), all vertical FOV 60°: 1.000130–1.000537 |

The disk now normalizes angular support and local pixel coverage, applying the
terrain's existing rain factor once. C0/C4 alone become RGBA32F. The
[intentional storage-only negative](native/solar-half-storage-negative-with-peak.log)
clips all channels at 65504 in queried RGBA16F and fails with ratios
0.250/0.255/0.264; shipping 32F retains peaks
264984.125/259095.609375/250262.796875. This negative is not the installed pack.
The [first aperture-guard failure](native/solar-radiometry-fixture-aperture-failure.log)
was a fixture matrix-reference error, not the shader's radiometric RED.

The [initial full-suite failure](native/solar-shore-candidate-full-check.log)
used the obsolete underwater Sun-presence upper bound 360; finite observed
7372.63 exceeds that old unit convention. Only the test bound was recalibrated
to declared solar irradiance/projected support and independent normal-entry
Fresnel transmission. The [calibrated result](native/solar-underwater-calibrated-presence-green.log)
does not prove integrated underwater energy or constitute another shader fix.
The [final native suite](native/v0.6-full-native-check.log) passes 11 graphics
pairs, three compute programs, retained water/atmosphere/caustic/wave regressions,
the shore response and all five clear/rain/coverage Solar cases on RTX 3080 Ti,
NVIDIA 580.173.02, native GL 4.6. These are correctness probes, not Minecraft FPS.
See the [solar review](../../docs/reviews/codex-solar-coverage-review.md) for
local pixel-mapping, empirical weather and refractive-radiance limitations.

## Actual Minecraft/Iris evidence

The UUID-guarded disposable V2 [run](real-view/run.json) completed all 16 scenes
at `2026-10-01T22:40:50.198622557Z`, with 2560×1440 window/framebuffer, 12/6
chunks, default pack options, VSync off, frame-limit setting 260 and 5 s warmup /
5 s measurement per scene. All scene captures record focus and active 0.6
without fallback. Focus is a capture observation, not continuous monitoring.
Minecraft records GL 3.2; native GL 4.6 is not substituted for that context.

The unchanged 1440p reporter accepts this run. The
[independent data audit](INDEPENDENT-AUDIT.md) verifies the copied 82 raw evidence
files, all 16 strict PNGs, 14,909 positive raw intervals, exact pack identity,
recomputed statistics and eye/contact/dimension metadata. The
[actual results](real-view/RESULTS.md) show mean 126.5–196.9 FPS across the 14
overworld/water/cave/glass scenes; Nether/End are separately about 415–421 FPS.
Worst observed interval is 10.601779 ms and none exceed the 16.667 ms reference.
These short warmed views plus one scripted boat-contact scene do not establish
new-chunk traversal performance, a general FPS floor or appearance quality.
The prior 1600×900 0.5 run is not a controlled performance A/B.

The real observer initialization reports `available=true`,
`bindingRestored=true`, target count 16 and all 12 requested main/alt images:

| Targets | Actual internal format, both images | Actual size, both images |
| --- | --- | --- |
| C0, C4 | RGBA32F (34836) | 2560×1440 |
| C5, C8 | RGBA16F (34842) | 2560×1440 |
| C6, C7 | RGBA16F (34842) | 1024×512 |

This matches declarations and establishes allocation at the observed boundary.
The read-only observer temporarily binds existing textures and restores the
binding; it does not allocate/write storage or read HDR pixels. CPU tests/build
are preserved in [their separate log](native/benchmark-0.3.4-build.log).
Neither storage observation nor an LDR image proves Iris disk-energy integration.

The [independent actual-image review](../../docs/reviews/codex-v0.6-visual-audit.md)
finds no obvious catastrophic regression, preserves underwater directional sky
and cave/glass/dimension compatibility, but confirms persistent cyan/mint
shallows, jagged dark/clear shoreline bands and stylized reflection ribbons.
Moving/boat stills and nonzero bridge forces do not establish temporal stability,
natural wakes or vanilla rowing. Resolution/wave/entity differences limit 0.5
comparisons to qualitative observation, not pixel causality.

## Saved-state cleanup and normal handoff

The [before-stop](fixture-before-test-stop.json) and
[after-stop](fixture-after-test-stop.json) read-only Anvil audits find all 390
approved unique reserved TEST cells exact AIR, zero non-AIR and no journal.
An independent repeat reproduced those checks. Completion flags alone were not
treated as saved-state proof; these remain specific-cell, not whole-world/entity,
audits. No ordinary-world test camera/time/terrain automation was used.

TEST Save/Quit stalled again. The
[bounded thread excerpt](test-shutdown-thread-excerpt.txt) and final audit record
describe the stopped shutdown path; only the identified TEST Java and its own
launcher were terminated afterward. **This was not a clean exit; neither its
cause nor a shutdown fix is established.** Benchmark JAR/marker are recoverably
inactive as `.0.6-release-disabled` copies.

The [normal handoff](ordinary-handoff.json),
[current](user-scene/current.png)/[paused](user-scene/paused.png) native images and
[independent addendum](INDEPENDENT-AUDIT.md#final-saved-state-and-ordinary-handoff-addendum)
record a fresh normal-account world launch with active 0.6/physics 0.2.0, restored
1600×900/cap 120/pause-on-lost-focus settings and verified pause menu. Options are
byte-identical to the pre-test snapshot, SHA
`02516270fea53cc286dceb1d5eca457f2ecc2e0ab6d2e1b15b01c4032307e5f0`.
Ordinary save/settings backups remain private in `build/`, not exported here.
The save tree matched the private post-save backup before normal relaunch per
root's bounded record; natural saves resume afterward. Whole launcher-config
byte equality or current ordinary-save byte invariance is not claimed.

## Remaining goal

Natural shore color/source handoff and moving highlights/refraction/wakes still
require acceptance. Coherent spatial cloud shade and convincing cloud shape are
open. General refracted radiance/index-squared (`L/n²`) and étendue transport,
nonlinear underwater disk coverage, arbitrary wet normals/bent shadows, water
membership and depth-resolved scattering are not solved by these tests. Large
off-axis/horizon coverage, rough-water direct-Sun quadrature, empirical weather
coupling and Moon normalization remain separate approximations/verification.
The local contact-wave model is not mass-conserving fluid simulation.

Continue the [full realism goal](../../docs/REALISM_GOAL.md); this checkpoint
closes only the evidenced increment and safe handoff, not that goal.
