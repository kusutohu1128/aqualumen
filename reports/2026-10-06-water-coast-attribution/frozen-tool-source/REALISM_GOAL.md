# Water and sunlight realism goal

Active user goal, begun 2026-10-02. The user wants convincing realistic water and
sunlight, including reproducible physical phenomena where useful, on this RTX
3080 Ti. A dedicated client Mod is allowed. The original60-FPS floor was relaxed:
visual quality is the priority, with honest actual Minecraft timing evidence.
The instruction to continue toward the goal is not satisfied by calling the
existing prototype finished or by passing only its existing tests.

## Last verified ordinary-runtime baseline

The last ordinary-runtime verified experimental
pack is 0.6.0, ZIP SHA-256
`6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`.
The retained 0.5.0 ZIP is unchanged, SHA-256
`88ff19eed363ff3d25287b3873ed7c0ac7b2ca654074e0365d510fedd07c859d`.
The frozen0.4 implementation is commit `6dd4e5a`, ZIP SHA-256
`5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069`;
its comparison images and distinct1440p timing evidence remain retained.
The previous 0.3.3 baseline, commit `a81c7ae`, remains the retained comparison
artifact with SHA-256
`ff81efa32c96f3b1c2c76c1c55fe6e32ed29f1344e67a239afeeccca980583e5`.
Its eye-coordinate and underwater directional-sky fixes are retained and must
not regress.
Physics bridge 0.2.0 and its persistent local wave solver are already installed.
These are a working foundation, not proof of the full visual goal. Normal-play
settings were restored byte-for-byte and development instrumentation disabled;
the user's ordinary-account world runs 0.6 and is paused at the recorded handoff.
The [0.6 verification](../reports/2026-10-02-v0.6.0/VERIFICATION.md) and
[independent final-handoff addendum](../reports/2026-10-02-v0.6.0/INDEPENDENT-AUDIT.md#final-saved-state-and-ordinary-handoff-addendum)
record that point-in-time evidence. This runtime handoff
does not complete the rendering goal, which remains active, not achieved.

## Requirements and completion evidence

- Water should look natural across shallow/deep water, shorelines, above/below
  the surface, changing view angles, lighting, rain and moving contacts. Remove
  demonstrated false-hit/fallback discontinuities; do not merely desaturate an
  incorrect geometry path. Judge original real Minecraft images and motion,
  backed by controlled production-renderer tests for the causal corrections.
- Sunlight, sky/cloud illumination, water highlights, shadows and underwater
  illumination should form a coherent light-transport model, with visible depth
  and plausible daytime/sunset/night variation. Check reflected/transmitted
  sky and direct-light source consistency rather than only isolated formulas.
- Physical effects must be described accurately: optical laws and transport,
  dispersed wind waves and persistent contact-wave dynamics are distinct from
  mass-conserving water movement. Extend useful physical effects when the visual
  goal requires them; do not call a decorative animation a fluid simulation.
- Verify temporal appearance: moving-camera water highlights/refraction and
  contact propagation must not be judged solely from one still screenshot.
- Preserve the ordinary user's saves, instance settings and assets; use only
  UUID-guarded disposable fixtures for automated camera/terrain operations.
  Preserve old releases and restore safe ordinary play after validation.
- Verify every introduced shader/module on real NVIDIA GL, all retained
  regressions, Minecraft/Iris activation without fallback, and affected natural
  scenes. Record raw intervals and visual limitations without an FPS guarantee.

Full-goal completion requires inspecting the final actual runtime evidence
against all requirements above. Finishing a vertical slice or documenting a
known visual flaw does not by itself establish completion.

## Current implementation and validation progress (not full-goal completion)

The first0.4 water slice separates opaque direct-Sun receiver radiance from
total shaded color, snapshots it before translucents, and focuses only a
confirmed refracted receiver's direct component. Production-main RTX3080Ti
tests establish zero-Sun invariance (former maximum RGB change0.0289524,
now0), red-only positive focusing0.0107598 with unchanged green/blue, and
zero proxy focusing (formerly0.000158489). Real terrain/deferred MRT copies
also match and remain immutable after later producer-buffer writes.

The0.3.3 underwater directional-sky/Fresnel/TIR/cave/eye tests are retained.
The continuous-bed production test now verifies a vanishing handoff change:
the former0.066329 RGB jump across approximately0.00004m becomes0.00000570714
in the preserved failing interval. Above-water topfaces finish a fixed solve
and blend separately transported hit/proxy radiances by numerical reliability;
underwater/vertical-face early-return policy stays unchanged. This does not
prove every discrete/occluded bank silhouette continuous.

Underwater composite zero-Sun variation0.0769311 now becomes0, positive red-only
direct attribution remains0.0285025, and nearer-depth layers reject behind-layer
caustics under both NEAREST/LINEAR input filters. Raw same-pixel depth snapshots
are paired with C8, before one eye-leg attenuation. Rejected-foreground-bank
controls and the final full native suite pass on RTX 3080 Ti OpenGL 4.6; these are
production-fixture results, not Minecraft timings or a full natural-shore proof.

The installed 0.4.0 pack completed 16 recorded Minecraft/Iris compatibility
scenes, including natural coast/river/ocean, underwater views, moving view,
scripted boat contact, cave water, glass and Nether/End. Four 0.3.3 comparison
scenes are also retained. The
[independent exported-data audit](../reports/2026-10-02-v0.4.0/INDEPENDENT-AUDIT.md)
verified 20 strict PNGs and all 18,506 raw intervals (3,889 before / 14,617 after),
pack identities and recorded scene metadata. Minecraft records GL 3.2 while the
native harness records GL 4.6; do not conflate the two contexts or evidence types.

The four saved A/B mean FPS values are lower in 0.4.0. Ocean-day and upward-near
water differ in capture-time focus (before focused, after unfocused), so those
changes are not pack-only causal comparisons; coast/river remain focused. All
candidate P99 values fit 16.667 ms, but dusk/night each contain one slower interval,
with worst 21.775271 ms. The strict 60-FPS floor was relaxed, and no all-frame floor
or arbitrary-world performance guarantee is claimed.

Natural images still show strong shallow-water cyan and jagged/discrete shore
transitions. The controlled continuous-bed correction does not establish that
those visual defects are solved. Three replacement0.4 full-window1600x900 clips
were recorded and reviewed: image coverage is valid, but natural boat/wake motion
is not accepted. Scripted boat translation contains a sharp relative-geometry
change and the wake is mostly outside the forward view; it is not vanilla rowing.
See the preserved0.4 visual audit and temporal-video audit. These separate
recording workloads do not replace1440p performance measurements.

The0.5 incident-Sun slice adds the mean-horizontal-interface Snell beam path,
exact Fresnel entry loss and RGB Beer attenuation to the paired raw direct-Sun
component, before the existing separate outgoing attenuation. Three genuine
production-main RED/GREEN increments prove incident-depth response, absolute
normal-entry energy and above-water two-leg response. Zero-source/non-Sun
controls and all retained regressions pass. C8 remains immutable air-lit source
attribution, not a pre-attenuated source. This is not arbitrary-normal/bent-shadow
transport, a water-membership proof or a depth-dependent in-scattering solution.

The0.5 [16-scene real-view run](../reports/2026-10-02-v0.5.0/real-view/run.json)
and [independent audit](../reports/2026-10-02-v0.5.0/INDEPENDENT-AUDIT.md) verify
16 complete1600x900 PNGs and24,701 raw positive intervals, active88ff19 pack and
all16 focused captures. The unmodified1440p report verifier deliberately rejects
this resolution; this is a separate quality/compatibility audit, not a claimed
1440p benchmark. The [visual audit](reviews/codex-v0.5-visual-audit.md) finds the
cyan/serrated shore issue persists;0.5 temporal naturalness is unverified.

The [ordinary handoff](../reports/2026-10-02-v0.5.0/ordinary-handoff.json)
verifies a fresh normal-account launch with0.5/physics0.2.0 and disabled benchmark
controls,1600x900/cap120 restored options and a paused native game view. Ordinary
world automation was not used; natural saves resume after normal launch. The
instrumented TEST-client shutdown stall remains unresolved; its cause is not
established or claimed fixed. Continue controlled shore optics diagnosis, natural motion,
coherent spatial cloud shade and calibrated sunlight. Cloud/light and other
full-goal requirements remain open.

At the initial post0.5 checkpoint, the [stepped-shore diagnostic](../reports/2026-10-02-shore-diagnostic/README.md)
ran deterministically through actual production main, with a closed bank,
independent depth/color inputs and positive reflection/bed controls. Initial
large jumps were fixture-boundary/palette changes, not shader REDs. A qualified
same-input-face/color/coverage bracket responds to optical-normal/fragment-depth
ablations but not environment-only SSR. Actual refracted receiver identity and
source continuity were unproven, and other switches persisted. This evidence
narrows the next causal investigation; it does not justify a shipping shortcut
or a claim that natural shoreline artifacts are fixed. Installed0.5 was unchanged
at that diagnostic stage; the subsequent bounded0.6 correction is recorded below.

The initial [solar-radiometry source review](reviews/codex-solar-radiometry-plan.md)
also identifies an actionable disk/direct-beam energy and HDR-range mismatch.
Its source-derived angular integrals are not a fresh GPU result; the proposed
actual terrain/deferred-main unity test was pending at that review. Its subsequent
RED/GREEN results are recorded below, rather than attributed retroactively to the
design review. The original60FPS floor remains relaxed; real timings are
observations, not that old acceptance gate. Full solar/cloud transport coherence
is not established by the bounded correction.

## Proven 0.6 checkpoint and unmet requirements

The 0.6 above-water topface search retains a visible deep receiver that the 0.5
fixed-point solve skipped while alternating between depth cells. Across the
same 48-micrometre perturbation, the public-main tagged-green response loss
`0.100883→0` becomes `0.100884780288/0.100881353021`: difference `3.42727e-6`,
within the unchanged independent physical/one-depth-pixel bound `0.001669252223`.
Foreground-bank, viewport, surface and residual guards remain; underwater and
vertical-face iteration policy is unchanged. The
[causal review](reviews/codex-shore-causal-review.md) and final-current
[native suite](../reports/2026-10-02-v0.6.0/native/v0.6-full-native-check.log)
establish this bounded correction, not natural shoreline acceptance.

Separate genuine production terrain/deferred-main clear and rain RED/GREEN
increments compare actual receiver beam irradiance with the disk's independently
integrated raw sky radiance. Clear ratios approximately `0.001357` become
`1.000123–1.000527`; rain-only ratios approximately `6.667` become
`1.000007–1.000205`. The angular-support/coverage normalization and existing
weather factor now agree within the unchanged 2% gate. Native 1600x900 and 1440p
FOV 60 cases, including one 0.37-pixel 1440p phase shift, also pass. Only C0/C4
are promoted to 32F; a deliberately half-float diagnostic clips at 65504 and
fails energy coherence. The old underwater Sun-presence upper bound was
recalibrated to the declared source units, without a shader change for that
oracle correction. See the [solar review](reviews/codex-solar-coverage-review.md)
and separately retained native failures/positive/negative controls.

The completed 0.6 [actual Minecraft run](../reports/2026-10-02-v0.6.0/real-view/run.json)
contains 16 active, nonfallback 2560x1440 scenes and 14,909 positive raw intervals.
The unchanged 1440p reporter accepts it; independent audits validate all PNGs,
identity/eye/contact metadata and recomputed timings. All captures report focus;
that does not establish continuous focus throughout every interval. For the 14
overworld/water/cave/glass scenes, mean FPS is 126.5–196.9 over 5-second samples;
worst across all 16 is 10.601779 ms. No new-chunk traversal or general FPS floor
is established. Actual Iris initialization observes C0/C4 main/alt RGBA32F,
the other queried targets RGBA16F and correct frame/LUT dimensions; this is an
allocation snapshot, not HDR pixel readback or an Iris energy-integral test.

The [0.6 visual audit](reviews/codex-v0.6-visual-audit.md) still finds cyan/mint
shallows, jagged dark/clear shore bands and stylized reflection ribbons. The
underwater curved sky window and cave/glass/dimension compatibility remain,
without an obvious catastrophic regression in the reviewed stills. Different
resolution/phase 0.5 images are qualitative comparisons, not controlled pixel
causality or a timing A/B. Moving/boat stills and measured contact input do not
accept temporal highlights, refraction, wakes or natural vanilla rowing.

The [ordinary handoff](../reports/2026-10-02-v0.6.0/ordinary-handoff.json) records
fresh normal-account 0.6/physics 0.2.0 activation, benchmark controls disabled,
original options byte-restored at 1600x900/cap 120 and a verified pause menu.
The before/after saved-state audits find 390 approved reserved TEST cells AIR
and no journal, not whole-world/entity integrity. TEST Save/Quit stalled again;
scoped termination followed the cleanup checks. A clean shutdown or defect fix
is not claimed. Ordinary saves naturally resume after normal relaunch.

Still unmet: natural-shore color/path handoff and motion acceptance; coherent
spatial cloud shadows and convincing cloud shape; arbitrary wet-receiver normals,
bent shadows, water membership and depth-resolved in-scattering; general
refracted-radiance/index-squared (`L/n²`) and étendue transport, including nonlinear
underwater disk coverage. The separate bottom-beam flux tests do not prove that
radiance convention or authorize a compensating factor. Horizon/large-off-axis
coverage, rough-water solar quadrature, empirical weather coupling and Moon
normalization remain bounded/approximate. **The full goal remains active.**

## Execution sequence

Post0.6, the [0.7 native-only candidate](../reports/2026-10-02-v0.7.0/WORK-IN-PROGRESS.md)
corrects a separately qualified sampled-facet SSR source loss: an existing
overshoot cutoff was narrower than the last actual march segment. Positive
source retention, off-ray/submerged tag negatives and all retained native tests
pass. Only above-water upper-interface crossing width changes; ordinary runtime
remains0.6 and candidate natural-view acceptance is pending.
At that 0.7 checkpoint an independent remote-camera-ray/local-bed fixture also reproduced a source-gain
change despite identical water geometry and local depth, in both frozen0.6 and
the0.7 candidate. That genuine optical-depth RED was unresolved there. The next
architecture needed shared actual local bathymetry between geometric and optical
waves, without shipping a global depth override to hide it. Those observations
do not certify all shore discontinuities or complete this goal.

The [0.8 native checkpoint](../reports/2026-10-02-v0.8.0/WORK-IN-PROGRESS.md)
implements the shared local-column field, its depth-gradient wave term and an
explicit coarse-facet fallback. The original remote-depth source-gain RED now
passes with actual valid fixture data; missing-input/mixed-primitive, physical
shallow/deep and derivative controls also pass. Physics0.3 supplies loaded-chunk
columns with a bounded cache, but is not installed or live-sampler validated yet.
An independently qualified new visible-bed condition exposed a further loss
from near-converged bisection/confidence mixing. A same-depth-reprojected proposal
fixes it while retaining all final guards; both NEAREST/LINEAR variants and the
retained native suite pass. These are production-fixture results only. Ordinary
runtime remains0.6/physics0.2; natural-coast/motion, cloud and full physical goals
remain open. Do not substitute these native passes for actual Minecraft quality.

The subsequent [0.8 isolated runtime checkpoint](../reports/2026-10-02-v0.8.0-runtime/README.md)
now proves actual named-sampler/storage/readback on the RTX3080Ti Minecraft
client, after a real-Fabric-metadata failure was fixed in test-only observer0.3.6.
The filled64² field has4096 finite valid columns and conditional saved-floor
corroboration; same-frame absolute-camera and final-fetch attribution remain
limits. Actual ocean/coast captures still show cyan/mint shallows and jagged
bands: the visual goal is not accepted. No new1440p benchmark or motion-quality
claim is made. Normal0.6/physics0.2/configs are restored, benchmark disabled and
the ordinary world is reopened paused. All five requirements below remain open.

1. Diagnose shallow-water cyan and shore discontinuities from actual production
   inputs. Test one reproduced behavior, implement it, and repeat. Prefer correct
   receiver/path/lighting provenance over cosmetic compensation.
2. Improve water's depth-dependent appearance and receiver illumination based
   on the findings, with clear optical assumptions and real-view comparisons.
3. Improve cloud shape/lighting and coherent sunlight/highlight appearance.
4. Validate moving views, waves/contacts and day/weather/dimension compatibility.
5. Audit the full visual goal and continue any unmet requirements. Do not mark
   the goal complete from code compilation or warmed-view timings alone.

Implementation and independent review are Codex work unless a genuine external
model invocation is explicitly recorded. Do not misattribute team agents to
Claude Opus/Sonnet.

The subsequent [shore-source atlas checkpoint](../reports/2026-10-02-shore-attribution/README.md)
separates transmission, reflection, confidence and raw opaque source color in
three actual captures. The coast's camera-site one-block label does not describe
the full viewport: an independent saved-bed profile confirms rapid deepening.
This rules out declaring every4–9m path erroneous merely from the site label.

The [world-coordinate shore checkpoint](../reports/2026-10-02-shore-world-r3/README.md)
adds actual same-frame FINAL-sampler RGBA32F reads at16 native coordinates,
independent program identity and verified11-state restoration. Explicit water-main
MRT payloads pair surface, transmitted direction, returned receiver/kind, four
path values, original opaque position/local depth and normal/Fresnel. Thirteen
qualified water points contain four hits/nine proxies; three are cleared sky.
The corresponding earlier PNG is not the same wave phase as the raw snapshot.
Saved full-cube ray traversal gives conditional real-terrain comparisons: three
accepted paths agree closely with first-floor distances, one accepted shore-edge
point differs, and proxy paths can be either shorter or longer than the first
saved intersection. Local vertical depth alone is not that ray distance.
The observer's missing-final-uniform/full-geometry flags remain false. No natural
visual fix, new shipping version or full-goal completion is claimed. The next
correct seam is an independently first-visible-bed-qualified production-main
source response, separating exploration seed from the unchanged miss proxy.

The [0.8.1 bounded correction](../reports/2026-10-02-v0.8.1/README.md) now separates
that exploration seed from the unchanged original-view miss proxy. A confirmed
local column supplies only a search hint; bank/viewport/surface/residual checks
remain. Actual original production-main NEAREST and LINEAR old-source REDs lose
the same independently qualified visible first shelf when only a remote floor
changes; the candidate retains its source/path and independently bounded absolute
Beer/Fresnel gain. Current archives also preserve neutral/tag mode0/2/3 and
repeat float images. All retained NVIDIA native tests pass before the actual
six-scene Minecraft run, which activates0.8.1 without fallback at1600x900.

Natural coast/river images still show broad cyan/mint and pointed dark bands;
cloud shape remains repetitive. Upward underwater stills do not show the old
rectangle/double-map seam but retain strong round curvature. Neither desired
underwater appearance nor motion naturalness is accepted. The ordinary configs
and physics0.2 are byte-restored after bounded TEST termination; current lifecycle
evidence distinguishes restoration-before-relaunch from an actual paused handoff.
The repeated TEST Save/Quit stall is not fixed. All full-goal requirements remain
open. The next causal slice enables real public wave geometry in the qualified
first-visible-bed probe, without replacing it with a cosmetic color adjustment.

That fixed [nonzero-wave slice](../reports/2026-10-02-v0.8.1/native-waves/WAVES-AUDIT.md)
now passes at phase1.25/WAVE_HEIGHT0.12/pixel65,48 with original VS geometry and
independent first-surface/source bounds. The first raster-envelope failure is
retained as INCONCLUSIVE, not shader RED. This is one NEAREST/explicit-triangle
fixture, not actual Sodium topology, wave-spectrum or natural-shore acceptance.

The completed [0.8.2 development checkpoint](../reports/2026-10-02-v0.8.2/README.md)
corrects an actual same-world receiver direct-Sun change tied to the observer's
cloud cache. Qualified fixed P/Q production-main RED/GREEN tests retain positive
spatial cloud extinction, absolute C5 bounds and actual deferred C8 retention.
All retained native tests pass, including the fixed nonzero-wave first-bed probe.
Actual nonfallback coast/river/ocean Minecraft captures at1600x900 recompute
mean94.42/91.07/67.25FPS; ocean1%low53.01 shows the new integration cost, not a
60FPS floor or1440p guarantee. Cyan/mint shallows, jagged bands and artificial
clouds remain; no new underwater or motion capture is recorded. Actual Iris C7
storage is observed, not a named-sampler/cache-pixel readback proof.

TEST Save/Quit again stalls; scoped TERM follows saved390-cell AIR/no-journal
checks. The exact test processes are absent and original configs are byte-equal
to pre-test backups, ordinary0.6/physics0.2 selected and instrumentation
recoverably disabled. At the restoration-before-relaunch checkpoint no fresh
ordinary paused handoff is claimed. Ordinary saved files match the fresh
post-user-play backup; no ordinary-world restoration or automation occurred.
The full goal and all remaining natural-appearance/motion/physical requirements
stay open. The next qualified slice checks the known direct receiver component's
[exiting radiance units](reviews/codex-water-sun-radiance-plan.md), not blanket
frame dimming, empirical desaturation or a redefinition of visual acceptance.

The subsequent [0.8.3 checkpoint](../reports/2026-10-02-v0.8.3/README.md)
corrects the known direct-C8 receiver component's water-to-air directional
radiance units. Two qualified original-main old-source REDs produce roughly
1.7769 times the independent source response; the direct-only exit correction
matches all RGB bounds, with serial native/cloud/nonzero-wave regressions passing.
This is not global darkening or a calibration of ambient/proxy/scattering paths.

Six actual focused1600x900 views activate exact0.8.3 without fallback. Raw3009
integer-ns intervals are independently recomputed; mean coast91.98/river88.81/
ocean66.15/underwater-up118.42–118.52FPS are warmed observations, not1440p or a
60FPS floor. Three actual submerged near/deep/tilt eyes have no visible old
rectangle/double sky map, but strong round curvature and dark outer regions
remain. Cyan/mint shores, pointed dark bands and artificial clouds remain too.
Natural appearance and motion are explicitly unaccepted.

After sampling, actual terrain/water named C7 sampler units, existing target
identity, two reserved-row cache texels and all11 restored caller-state fields
are observed. This closes allocation-only evidence for prepared inputs, not
specific fragment execution or same-frame producer freshness.
TEST Save/Quit still stalls; bounded saved390-cell AIR/no-journal checks precede
and follow scoped own-process TERM143. Original configuration bytes and ordinary
saved-file equality are verified before relaunch, with no ordinary restoration
or automation. Normal0.6/physics0.2 is then actually reopened and paused; later
Iris timestamp-comment regeneration is distinguished from byte restoration.

The full goal remains active. The next discriminating underwater seam is a dense
flat original-main directional marker map compared with independently projected
Snell/TIR geometry, then wave-normal/rim and offscreen-reflection missing-source
tests. A physical round window must not be erased merely to pass a cosmetic
image criterion. Shore/cloud/motion and broad physical/compatibility work remain.

The subsequent [underwater angular checkpoint](../reports/2026-10-02-underwater-angular/README.md)
captures the actual uploaded water-program matrices and verifies a native-only
flat directional map with an independently qualified positive reflection chain.
Serialized executions agree byte-for-byte; the captured-view angular subcheck
is positive but its full reflection qualification remains INCONCLUSIVE.
Natural wave-rim/dark-exterior appearance is not accepted. A separately qualified
near-reflector regression is the next implementation slice, not a claim that
the original natural image has been fixed.

Normal-account disposable V2 Save/Quit now cleanly saves all dimensions and
exits without a signal under the unchanged candidate/Mods, providing an effective
launch-identity workaround for the name-only TEST override. Runtime host-profile
causation is not proven. Ordinary0.6/physics0.2 was reopened paused at17:40:51;
its next normal Save/Quit at17:55:58 also cleanly saves all dimensions and the
owned client exits0 at17:56:24 before new GPU work. No ordinary-world automation
or restore occurred. This lifecycle evidence does not complete the visual goal.

The following [0.8.4 checkpoint](../reports/2026-10-02-underwater-reflection/README.md)
fixes a qualified first-visible0.3m underwater reflector missed by the previous
point's wrong projected-depth comparison. Original-main actual input readback,
independent lower gain/path bounds, real native RED→GREEN and a nonvacuous
black-first/red-background negative support only this local repair. All retained
native regressions pass. An actual Iris annotation parser failure in a diagnostic
pack is retained and corrected with four explicit clear-colour components;
public-ZIP CPU RED→GREEN and actual nonfallback loading are separately checked.

Three actual same-invocation atlas views and five shipping0.8.4 smoke views
remain visibly unnatural: dark water exterior/wrinkled round rim, cyan shores,
pointed jagged bands and procedural clouds persist. Atlas displays unknown
local-column and SSR-miss flags, despite ready CPU bathymetry; raw C9–C11
allocation/binding/readback is not proven. A known-column-only facet ablation
is not run because it may be inactive. The next causal seam distinguishes actual
raw column, vertex unknown and upward/downward-face classification without
changing the refractive index or forcing a known flag.

Matched-profile disposableV2 clients cleanly save/exit0 without signals; saved
390-cell AIR/no-journal checks remain positive. Ordinary saved files match the
fresh post-save backup before relaunch; no world restore/automation occurs.
Original configs and ordinary0.6/physics0.2 are restored, test instrumentation
recoverably disabled, and the actual ordinary game is reopened/paused at22:10:28.
Candidate0.8.4 is installed but not selected. The broader objective is unfinished;
neither the local repair nor the short1600x900 captures count as visual completion.

The [0.8.5 reversed-top checkpoint](../reports/2026-10-02-underwater-reasons/README.md)
now distinguishes the actual raw local-column query from the contributing-vertex
guard:16 actual FINAL water texels observe a negative top input normal, rawKnown1,
unknownWeight near1 and finalKnown0. The original production VS/FS native
same-top/winding RED has0.056715965m vertex displacement difference and0.14526148
optical-normal difference; the candidate gives exactly0 differences with all
qualified input, positive-wave, whole-C0 observation and repeat checks intact.
Negative faces use the local-column wave only when confirmed; fragment promotion
also requires every contributing vertex. A4m-column bottom and invalid-column
backtop remain undisplaced/unknown/unpromoted in separate bounded controls.

The corresponding after-Iris named-sampler readback observes unknownWeight0,
rawKnown1 and finalKnown1 at all16 points, with actual RGBA32F targets and restored
caller state. PNGs are different frames/phases, not a controlled pixel-difference
oracle. All retained native checks pass; five shipping1600x900 real scenes load
the new candidate without fallback. Actual stills remain visibly unnatural:
cyan/mint shallows and jagged dark bands, distorted submerged round-window rims,
dark exterior and procedural clouds persist. Motion is not accepted. Short
captures do not establish a1440p result or an all-frame60FPS floor.

The normal0.6 baseline is not replaced by this development candidate. A further
thin-bottom/topology boundary is not covered by the4m negative: the existing
surface-height tolerance is0.12m. Pinned Sodium bottom planes and minimum top
corner heights offer a separate local discriminator; test that next rather than
globally narrowing the shared column tolerance or claiming every bottom safe.
Offscreen reflection provenance, natural-shore transport, cloud appearance,
temporal contacts and all broader physical/compatibility goals remain open.

The [0.8.6 thin-bottom checkpoint](../reports/2026-10-03-thin-water-topology/README.md)
now reproduces the .12m same-height alias on a supplied1/9 column and pinned
Sodium bottom. Original VS displacement1.5725mm and final-known/top promotion
become zero displacement and rejected promotion with ONLY a negative-known
VS fractional-height discriminator. Shared tolerance, FS, wave/optics/transport
and positive-top fallback are unchanged. Same-binary native RED→GREEN,25
opposite-winding top envelope controls and5 front-facing air-side bottoms pass;
all retained native regressions pass. Primary bytecode provides a possible
slime-floor counterexample; live thin-sheet meshing is NOT reproduced. The
guard is bounded to pinned vanilla topology/normal heights, not arbitrary Mods.

Five actual900p shipping views load0.8.6 without fallback under exact disposable
V2 guards, with independent PNG/pose/raw-ns audit. Severely undulating submerged
sky rims/dark exterior, cyan/mint shores/jagged bands and procedural clouds
still fail visual acceptance. Short capped frame observations do not establish
1440p, a guaranteed FPS floor, motion or completion. Both owned clients save
all dimensions and exit0 normally; persisted390-cell AIR/no-journal cleanup and
ordinary saved-tree identity before relaunch pass. Original configs are restored,
test instrumentation recoverably disabled, and ordinary0.6/physics0.2 is
actually reopened/paused at05:03:29. The candidate is installed but not selected.
Unknown/mixed-top symmetry, coarse-geometry/optical-facet consistency, physically
grounded offscreen reflection, shore/cloud/motion and the FULL goal remain open.

The [resolved-normal diagnostic](../reports/2026-10-03-underwater-resolved-normal/README.md)
retains the same factor4 geometry but lowers only known underwater optical wave
detail. Actual deep-water fine folds/holes visibly decrease; near/tilted rims
change and retain ripples, while the dark exterior remains. Seven bounded
native height/slope checks pass, but overall v2 stays strict RED for tiny air
bitwise differences; v1 remains INCONCLUSIVE. Neither the cutoff nor appearance
is adopted. The normal0.6/physics0.2 runtime was actually reopened paused.

The [residual-interface experiment](../reports/2026-10-03-water-residual-interface/EXPERIMENT.md)
now implements an unused-in-production TEST helper and pinned diagnostic-pack
hook: resolved mean plus declared independent missing-power directional slope
covariance, Gaussian9-node projected-area quadrature and per-ray Fresnel/TIR
source evaluation. The same actual4stage native binary first fails on the
pass-through stub, then passes with the implemented operator. Seven directional
source responses and constant-source C0 consistency, passive/repeat/negative
controls are independently audited. This is concrete optical integration
progress, not full dielectric/physical energy, quadrature-convergence, actual
Iris or natural/temporal acceptance. The finite-node model excludes unobserved
masking/offscreen geometry and can fall back discontinuously on rejection;
critical-angle, zero-residual and covariance-rejection tests remain required.
Existing frozen failures and shipping sources are preserved. The full objective
and shore/cloud/light-unit/motion requirements remain active, not achieved.

The same residual slice subsequently retains an actual invalid-covariance
guard RED, then passes the unchanged boundary binary after strict negative
Schur-remainder rejection; zero residual and nonzero all-TIR controls pass.
A separate double arithmetic oracle checks12 selected points, not a critical
sweep or energy test. The original tracer and STORE-only observer passivity
checks pass with the corrected helper. Actual Iris CONTROL/TEST near/deep/tilt
captures and later selected FINAL readbacks confirm48 applied TEST points;
no-fallback and four linked TRANSLUCENT stages/arity3 are observed, not exclusive
water draws or node invocation count. The actual inactive C13–15 descriptor
tooling RED is preserved before its bounded test-first parser fix. Root23 CPU
tests pass. Appearance is not adopted: separated bright sun points and rim
striations require angular-source/critical-boundary diagnosis and refinement.
Normal0.6/physics0.2 has been restored and freshly viewed paused again; old
strict RED and frozen packets remain unchanged. The full objective stays active.

The [angular-source diagnosis](../reports/2026-10-03-water-residual-angular/README.md)
now reproduces bright-point splitting in actual native water main with a
derivative-free narrow Gaussian source, on the same5,025 known/eligible/valid/
applied pixels across GH3/GH9/GH17 and four source controls. Original geometry,
covariance, transport and source units are fixed. Sparse sampling is supported
without stock solar derivatives or applicability switching in this bounded
reproduction; neither is excluded for natural critical/rim/native-Sun cases.

Independent double finite-rule arithmetic matches156/156 selected actual
samples (original84 plus separate source-positive72). Continuous finite-window
integration qualifies34/39 reference cases; the original five tiny narrow
references stay INCONCLUSIVE. At the bright pixel, actual GH3 red0.09712414
contrasts with the qualified reference0.01305445; at the center GH3 nearly
misses reference0.00862005. GH17 is not a converged truth or monotonic cure.
Narrow component counts5/3/4 versus broad1/1/1 are descriptive, not adoption.
This turn is numerical diagnosis/tooling progress, not an implemented optical
fix, new Iris scene, energy/reciprocity proof or full-goal completion.

Normal0.6/physics0.2 is actually reopened and freshly viewed paused10:35:21 after
all native work; original options/benchmark bytes and prelaunch ordinary-save
identity pass, with no world restore or camera/time/terrain automation. Iris
only regenerates its timestamp comment. Shipping sources and old strict
failures remain preserved. A light-domain sharp-source integral with verified
inverse Snell/Jacobian and unchanged stock solar units is the next bounded
correction, followed by actual Iris/rim/motion qualification. All broader
natural shore/cloud/physical/contact requirements remain active.

A separate [CPU inverse-Snell checkpoint](../reports/2026-10-03-water-residual-light-mapping/README.md)
adds the qualified exact-unit light-to-normal mapping and slope/solid-angle
Jacobian. Two public-API wrong-implementation REDs become GREEN; six CPU tests
pass, with five finite-difference determinant errors at most3.009e-9. This is
concrete mapping implementation progress, not a Gaussian/source integral,
binary32-input/GLSL, physical-energy, native Sun or natural-rendering fix.
The actual-main source-integral RED→GREEN and subsequent Iris/rim/motion checks
remain required. Shipping and ordinary-runtime assets are unchanged.
The same ordinary client is freshly re-viewed paused at10:51:58 after these
CPU-only checks; no subsequent native GL or ordinary-world automation occurs.

The [passive native-Sun reason checkpoint](../reports/2026-10-03-water-residual-sun-reasons/README.md)
now adds TEST-only first-failure/group accounting without changing physical
predicates or shipping selection. Root21 new CPU tests and retained native
checks pass. Independent full native replay verifies270 finite maps,135 exact
repeat pairs and175 comparisons with passive difference0. However actual Iris
near retains the unchanged minimum4 **negative** gate:2/16 applied; first
failures facet/critical10, reflection-hemisphere2, reconstruction2. Native-wide
reflection dominance does not generalize to that selection. No reflected-only
patch is adopted; exact binary32 forward-support/critical-boundary replay is
the next seam, not tolerance or presentation tuning. Current Iris reasons do
not contain raw n/v/Sun/targets and cannot prove which compound subpredicate
caused those ten failures. Optical, AA, full-frame visual, motion and shipping
acceptance remain false. Normal0.6/physics0.2 is restored and freshly viewed
paused14:59:53, with no ordinary backup restore or later native GL. The full
realism objective remains active, not achieved.

The [stable inverse-Snell checkpoint](../reports/2026-10-03-water-snell-boundary/README.md)
now implements a TEST-only pure GLSL node, with supported-critical numerical
RED→GREEN on the actual RTX 3080 Ti. All325 fixed inputs pass independent and
root replay:307 supported/18 absent, max XYZ error2.974e-8 and T/J relative
error5.267e-8. Root23 new CPU tests and retained11 native program pairs pass;
six derived48-node interior source-response sums match both references within
unchanged bounds. The old node rejects18 positive critical inputs;22 additional
saved-input strict-vector failures are not old whole-wrapper defects. Raw view
and eta remain fixed, generated-target direction semantics are explicit, and
the guarded inverse uses FP64 internally without changing production admission.
It is not included by water main/cap or installed into shipping. The previous
actual Iris2/16 negative gate and legacy full/base tilted-fixture exclusion
remain. Actual-input attribution, TEST main integration, support/visibility,
critical/rim convergence, pixel-AA, Iris/motion, performance and energy proofs
remain required. Normal0.6/physics0.2 is reopened and freshly viewed paused
15:48:48; no ordinary comparison copy was restored or later native GL run.
This is concrete bounded optical-arithmetic implementation, not fish-eye or
full-goal completion.

The [prepared-view reuse checkpoint](../reports/2026-10-03-water-prepared/README.md)
now proves a TEST-only local view/eta integer-context hoist on actual RTX3080Ti:
376 fixed standalone inputs preserve classes/rawbits/six interval triples;
the corrected independent reader and root replay verify every role/repeat.
Two actual original-water-MAIN runs pass6 fixed scenarios with zero binary32
bit differences, unchanged geometry/TES/depth/optical output and full48 direct
target/view/class/count ledgers. Each independent audit verifies648 capture/
depth maps,1,728 node maps and396,294 full-view ledger pixels. Predeclared
9-pixel arithmetic verifies1,440 both-mode records/720 unique raw inputs,
not every-pixel physical truth. All called MAIN nodes are supported: standalone
absent/unknown proof does not close MAIN or Iris branch coverage. Per-node
all48 optical neutrality retains producer exact hashes, not independently
recomputed per-node C0/depth/TES raw archives.

Draw-only native ABBA timing shows3.62–11.57% lower active medians over the
two runs; controls have small mixed changes, central absolute medians drift
23–24%, and outliers remain. This is not Minecraft FPS, universal/significant
speedup, a60FPS floor or ordinary-pack acceptance. No pack/Mod/config was
installed for this slice. All retained native checks pass; corrected auditor,
host-guard, timing-state and orchestration failures stay recoverable. The
ordinary comparison save is never restored. Normal0.6/physics0.2 is actually
reopened and freshly inspected paused20:48:38, with TEST entry points disabled
and no subsequent native GL. Next is reversible TEST integration/actual Iris
qualification, then remaining optical-band/rim work. Shore/cloud/transport/
energy/motion and the FULL realism goal remain active and unachieved.

The [prepared actual-Iris checkpoint](../reports/2026-10-03-water-prepared-iris/README.md)
now packages that local view/eta hoist reversibly and qualifies new TEST physical,
reasons and inputs clients. Root13 new CPU tests and retained11 native pairs
pass. Six actual900p physical archives contain871 retained intervals; matched
near/deep/tilt mean FPS improves11.66/13.57/16.69% in one sequential old/new pair.
Fresh ZIP authorization/hash cost is unchanged in policy but grows with the
embedded archive, so this is not isolated GPU causality, a universal speedup,
60FPS acceptance or normal-pack timing. Actual linked geometry hashes match.

Independent saved-reader replay and root reruns verify512 selected old/new
binary32 components exactly equal. Reasons preserve12/16 application and all
768 certificate calls (502 absent/266 supported/0 unknown); inputs retain four
supported category3 first targets, not all48 raw inputs/TES/application proof.
Unknown natural branch and simultaneous-draw evidence stay unavailable. Root
inspects all six stills; near/tilt PNGs byte-match, deep has particle differences.
Fine broken bands and polygonal rim remain, not fixed or physically accepted.
Next is the separately instrumented one-variable pre-Cholesky GH lattice-phase
diagnosis, not tolerance/blur/gate removal or automatic shipping promotion.

All TEST entry points are disabled; original configs and normal0.6/physics0.2
restored, ordinary save comparison matched before reopening without restoration
of a backup. Actual normal ordinary client is freshly inspected paused21:55:02,
with no later native GL. Shipping, motion, shore/cloud/transport/energy and the
FULL realism goal remain active and unachieved.

## Same-model conditional sampler checkpoint, 2026-10-06 12:34 JST

The [conditional-sampling evidence](../reports/2026-10-06-water-conditioned-sampling/README.md)
adds orthogonal Gaussian proposal axes and analytic conditional support without
changing raw normal/view/covariance, source units or survivor-mass normalization.
CPU16x4096 means meet all four retained T/R coefficient gates; this is not a
statistical confidence/temporal or low-ray-count convergence proof.
NVIDIA standalone port3904 scalar comparisons meet predeclared node gates after
a genuine CDF-only correction (max transmitted z error5.23e-5 ->3.68e-6).
Old rejected maps are retained. Proposal x remains CPU-generated.

A real tilted-camera MAIN now sees actual underwater opaque reflected sources,
with matched depth/geometry/inputs and a positive green-only C4 control. Both
dense and64-proposal source paths execute; the64 path sees48 reflected hits and
16 explicitly counted misses. Its green response differs from the dense result
by about0.43%, not accepted as converged first-visible-object transport.
Ten source/Sun/rain/opaque/cave/Moon cases retain exact raw controls. The64-ray
finite estimator matches its CPU replay, while its diffuse transmission error
9.246e-5 exceeds the unchanged6.883e-6 dense-reference gate. The native one-TEST-
pixel257x257 timing median9.578ms is still costly; it is neither Minecraft FPS
nor full-frame cost. Native regression suite11 pairs passes on RTX3080Ti.

No new candidate installed or candidate Iris/motion/visual acceptance claimed.
Normal0.6/physics0.2 reopened and root inspected ordinary runtime12:34:13 and
pause12:34:37, exact ordinary lock FD154. Save identity matched before reopening
without restoration; configs/Mod assets and disabled TEST entrypoints retained.
No native GL after handoff. Full natural shore/cloud/volume/radiance/weather/
night/contact/motion/energy goal stays active. Next is efficient same-model
inverse-CDF/proposal convergence, actual source and cost qualification, then
guarded disposable-world Iris validation; not automatic promotion of this slice.

## Same-model fast inverse and probability-panel checkpoint, 2026-10-06

The [fast-inverse/probability Evidence](../reports/2026-10-06-water-fast-inverse/README.md)
implements an independently fitted selected inverse and per-support-panel
probability quadrature, without changing raw optics, known masses, source units
or gates. Actual original-MAIN diffuse transmission RED9.2433e-5 becomes
GREEN5.38855e-7; wide-opaque7.55059e-7 also meets its retained dense gate.
Ten source cases/920 raw comparisons and native11 retained pairs pass.
Separate same-session one-TEST-pixel ABBA qualifies inverse-only speedup2.868x,
and fast64/probability8 speedup1.157x; neither is Minecraft FPS/full-frame cost.
Constant-source CPU4-context T/R success does NOT qualify actual object-source
convergence: reflection order8 is0.707% above retained dense and order12 is6.70%
below it. Higher order worsens that response; first-visible/source boundaries,
critical/general inputs, practical full-frame cost, Iris/natural/temporal/energy
and the full shore/cloud/physical goal remain open. No candidate installed.

Fresh41-file save identity and normal configs/Mod set/TEST disablement pass
before ordinary relaunch, with no save restoration/ordinary-world automation.
Normal0.6/physics0.2 runtime is freshly inspected13:01:38 and paused13:02:13,
owned handle16740 / hostJava3202154 / exact ordinary lockFD154. No native GL
after handoff. All old seals/failures preserved; goal remains active/unachieved.

## Observed-source viewport-exit correction checkpoint, 2026-10-06

The [source-boundary Evidence](../reports/2026-10-06-water-source-boundary/README.md)
isolates a real original-MAIN SSR omission: a coarse offscreen endpoint skipped
an independently known observed-plane receiver. A passive per-node observer
retains all optical MRT/depth bits. A one-variable last-in-viewport-segment
correction recovers1/6 misses in128/288-node conditions, with all previous
positive sources/path values retained exactly and no new outside hits. The
qualified function is implemented in production; retained11 NVIDIA pairs pass.
Actual first-plane RED6 -> GREEN0 does not prove arbitrary first-object geometry.

Corrected few-node source integration still differs by about1% from a finite
96-order dense rule: convergence remains rejected, with no relaxed gate.
Affected ten-case MAIN sources are prepared but not executed at this checkpoint.
No candidate installation, new Iris visual/motion acceptance, Minecraft FPS or
physical-energy proof. Full natural shore/cloud/volume/radiance/weather/night/
contact/motion goal remains active and unachieved.

Fresh41-file save comparison passes before ordinary relaunch without restoring
any save. Normal0.6/physics0.2 is reopened and root inspected runtime13:24:07,
pause13:24:13 JST; owned handle54078 / hostJava3220839 / ordinary lockFD154.
Original options/benchmark bytes, Iris noncomment properties, assets and disabled
TEST entrypoints are qualified. No native GL after handoff; old seals preserved.

## Affected MAIN and dense-source refinement checkpoint, 2026-10-06

The [boundary-regression Evidence](../reports/2026-10-06-water-boundary-regression/README.md)
now executes the prepared corrected ten-case MAIN sources:920 raw comparisons
and both unchanged selected dense transmission gates pass. With only the dense
quadrature table varied, corrected reflection orders96/128/192 give
.07443220913 /.07440861315 /.07439509779, adjacent changes.031711%/.018167%.
Independent cross-order replay qualifies234 input/geometry/non-rule comparisons
and113 raw controls per order. Finite192 is not certified truth. Dense variation
alone appears insufficient to explain remaining~1% few-node source differences;
efficient observed-source/critical/general geometry qualification remains open.

No new candidate installed, modified-candidate Iris/appearance/motion acceptance,
FPS measurement or physical-energy proof. Full realism goal stays unachieved.
Fresh41-file ordinary save/config baseline matches before reopening without any
save restore or ordinary camera/time/terrain automation. Normal0.6/physics0.2
runtime root inspected13:33:41 and final pause13:34:04; owned handle87409 /
hostJava3229665 / namespace16 / exact ordinary lockFD151, TEST disabled.
No native GL after reopening. The previous801-file source-boundary seal is
preserved; current liveness always requires revalidation rather than this note.

## Known-source boundary partition and SSR precision RED, 2026-10-06

The [observed-plane checkpoint](../reports/2026-10-06-water-observed-plane/README.md)
implements a CPU-only quartic window/fade partition with unchanged raw Gaussian
optics, mass, facet offset and source units.288 saved-input nodes +10,537
independent geometry queries and3 tests pass;440 previous numeric fields replay
exactly. Selected low-order known-plane/fade unit-response gates pass, but this
different functional is not actual SSR, arbitrary world geometry, GLSL or Iris.

An actual original-MAIN path/Beer precision RED is separately retained: first
center-source unit error.00173661 exceeds unchanged.00018419 gate, from returned
1.11961317m vs independently observed first-plane1.09716375m. All97 saved hit
confidence values are1; path/refined-UV precision, not those confidence values,
is the next causal seam. Actual binary32 camera/depth reconstructs receiver
Z=-5.99981689453125, not nominal6m; initial audit mistake/failure remains saved.
No shader/candidate installation, native GL or real-view improvement claimed.

Normal0.6/physics0.2 is freshly reinspected paused13:45:18; live owned87409 /
Java3229665 / namespace16 / ordinary lockFD151, TEST disabled and configs/assets
qualified. No ordinary save restoration or camera/time/terrain automation.
Full appearance/transport/cloud/physical/energy/motion goal remains unachieved.

## Actual SSR precision correction and current-renderer Iris checkpoint, 2026-10-06

The [path-precision evidence](../reports/2026-10-06-water-path-precision/README.md)
fixes the qualified actual original-MAIN Beer/path RED by changing only SSR
hit-refinement bisections4->12. All85 unchanged center gates pass; node0 unit
error.00173661 becomes.00000402472. All97 hits/191 misses and10,246 exact raw
input/geometry/weight/coarse-bracket/unrelated-MRT comparisons remain qualified.
Maximum97-hit path error.04507645m becomes.000176032m with the same actual
binary32 depth/camera reference. The tested function is adopted identically in
production. Retained11 native pairs/behaviors and a qualified nonvacuous closed
black-FIRST/red-BACKGROUND negative pass on RTX3080Ti; no tolerance relaxation.

A NEW exact-current-source TEST candidate is now genuinely run in actual Iris
at2560x1440/render12/sim6:9 native PNGs,3478 raw intervals, no fallback, all
capture windows focused, measured underwater poses/heads and scripted boat
contact. The original strict reader passes. Observed mean FPS ranges28.66rain
to118.57night; coast50.89/day35.77/moving44.15/boat62.96. These short workloads
are neither a4/12-only causal comparison nor a strict60FPS release gate.
The candidate includes preexisting uncommitted renderer work, not the native
probability12 TEST observer; normal0.6 assets/defaults are not promoted.

Separate900p20s/480-frame full-window moving-view footage and3 inspected decoded
samples are retained. Recording overhead never affects preceding1440p results.
Root inspects all9 native images: the old nested rectangular sky overlay is not
visible, but rough Snell-window rims, strong cyan/serrated shore and directional
streaks remain. Dome curvature alone is physical, not proof of an error. Whole
motion/contact naturalness, practical/general source integration, arbitrary
geometry, full coherent Sun/Moon/cloud/volume/physical-energy goal remain open.

TEST client exits0; a fresh41-file ordinary save/config baseline stays exact
through TEST and before reopening without any save restoration/ordinary-world
automation. TEST JARs/marker are recoverably disabled; normal0.6/physics0.2
reopens on owned62875/Java3253171/namespace16/ordinary lockFD154. Root inspects
native runtime14:00:29 and paused handoff; final checkpoint has the exact pause
image. Original options/benchmark bytes, Iris noncomment properties/assets and
disabled9 TEST entrypoints pass. No native GL after reopening; old seals retained.
The full realism goal is active and unachieved, not redefined as this correction.

## Actual natural-coast receiver/proxy witness, 2026-10-06

The [coast-attribution evidence](../reports/2026-10-06-water-coast-attribution/README.md)
adds two focused actual1440p coast atlas runs,499 raw intervals and bounded live
FINAL RGBA32F sampler qualification. Eight spatially separated dark/bright pairs
all match refraction miss/confidence0 vs opaque hit/confidence1. All16 are known
water, vertex-unknown0 and SSRmiss=-1; Fresnel.0489–.1194. Knowledge and SSR
switches do not explain these selected interior bands. Receiver/proxy transport
is strongly correlated, not yet a proved solver/visibility defect or correct
first-object/water-membership path. Same-invocation exit/search witnesses plus
independent first-visible geometry are next; no appearance-only fallback change.

Diagnostic Iris parser RED->GREEN and early-frame allzero readback rejection are
retained. Exact source recovery passes; production renderer/dist are unchanged.
Observed warmed5s means49.91/50.09FPS are diagnostic snapshots, not production
cost/quality/motion acceptance. PNG/selected raw are different frames; native
compile-only, live typed-sampler roles and source-neutrality evidence remain
separate, without an asserted C0/depth GPU-equality or general physical proof.

All TEST clients exit0. Original configs/threeJARs and41 ordinary saved files
match the fresh baseline before normal reopening; no ordinary-world automation
or save restoration. TEST controls disabled recoverably. Fresh normal0.6/
physics0.2 runtime14:17:48 and pause14:18:31 are root-inspected: owned68513,
Java3268991, exact ordinary lockFD154, window62914567 DISPLAY=:1. Old seals
retained; no native GL after ordinary reopening. Full realism goal remains active.
