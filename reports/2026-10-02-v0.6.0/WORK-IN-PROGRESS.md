# 0.6 shore search and solar-radiometry checkpoint

2026-10-02. Full realistic water/sunlight goal remains active. This is a
checkpoint, not a claim of full visual completion. Implementation and reviews
are Codex work, not a new Claude invocation.

Final checkpoint update: 2026-10-02 JST, following the saved-state/handoff audit
at `2026-10-01T22:56:30.332453Z`. The original native-stage pending runtime and
lifecycle items below are superseded by the completed
[verification record](VERIFICATION.md) and
[independent final addendum](INDEPENDENT-AUDIT.md#final-saved-state-and-ordinary-handoff-addendum).
The full visual/physical goal and TEST shutdown defect remain open.

## Frozen candidate and retained baseline

Candidate `dist/Aqualumen-0.6.0.zip`:
`6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`.
Retained0.5 ZIP is unchanged:
`88ff19eed363ff3d25287b3873ed7c0ac7b2ca654074e0365d510fedd07c859d`.
Physics0.2.0 remains unchanged. Benchmark0.3.4 is a separate development tool,
not a required normal-play Mod; SHA
`23dee6585808ff830cb5aae823751ef682696475bd86c19efb1ea1412b43347b`.

## Actual-production corrections and evidence

The shore regression tracks a physically visible uniform receiver across a
48-micrometre boundary perturbation, varying only its tagged green radiance.
The0.5 fixed-point iteration alternated depth cells and skipped a valid
intermediate receiver. The original response changes0.100883→0. The new search
bisects a sampled crossing on above-water topfaces; every existing surface,
foreground-bank, viewport and final-residual rejection guard is retained.
Underwater/vertical-face iteration policy is unchanged.

Measured corrected responses0.100884780288/0.100881353021 differ3.42727e-6,
within the independent physical plus one-depth-pixel bound0.001669252223.
Positive reflection/bed controls and full-image observation-neutrality pass.
This does not prove all discrete silhouettes or natural shore visuals fixed.
See the [independent causal audit](../../docs/reviews/codex-shore-causal-review.md).

The separate Sun regression uses real terrain/deferred mains and independently
integrates their raw sky output over spherical pixel solid angles. The old sky
disk delivers only0.001357.. of the actual direct beam. The new disk uses its
projected angular support and local pixel coverage; C0/C4 alone become32F.
The first clear test passes at512-square/2-degree FOV. A subsequent rain-only
test fails at a6.667 ratio; matching the existing weather factor exactly once
passes. This factor itself is not physically calibrated rain/cloud transport.

Fresh1600x900 and2560x1440/60-degree native cases pass the unchanged±2% gate;
the1440p case also passes with a0.37-pixel horizontal phase shift. Their ratios
are about1.00013–1.00054. A deliberate storage-only16F variant, not installed,
clips all peak channels at65504 and delivers only0.250/0.255/0.264 of the beam.
32F retains peaks264984.125/259095.609375/250262.796875. See the
[independent solar audit](../../docs/reviews/codex-solar-coverage-review.md).

The old underwater Sun-presence test initially fails its obsolete360 maximum:
measured7372.63 is finite and positive. Only that test bound was corrected to
the declared solar irradiance divided by projected disk support, times the
independent normal-incidence Fresnel transmission. Presence, all-channel peak
bounds, directional sky, opaque geometry, cave darkness, Moon and TIR guards
remain. This is not a new shader fix or integrated underwater-energy proof.

`native/v0.6-full-native-check.log` passes the complete retained suite plus the
shore, clear/rain,900p/1440p and phase cases on RTX3080Ti/nativeGL4.6.
These are GPU correctness tests, not Minecraft timings.

## Preservation and provenance limitations

`native/shore-causal-artifacts.tar.gz` preserves both original and corrected
causal/response inputs and raw outputs. Its GREEN tree contains a stale copied
`red.log`; the actual corresponding GREEN stdout is the separately preserved
`native/shore-visible-bed-first-green.log`. Do not treat that stale log as a
matching execution result. The initial causal tree also contains a CPU-only
palette-metadata bug; the corrected causal tree fixes it without changing the
actual production rendering. Both are retained, not silently overwritten.

The first failed full suite and old presence-limit diagnostic are preserved
separately from the complete passing suite. Earlier clear/rain probe headers
are retained alongside the current one. New0.3.4 observation tests/build pass,
but a CPU mock boundary alone does not establish actual Iris allocation. The helper
queries existing targets and restores texture binding, without creating or
modifying pixel storage. Those runtime items were pending at the initial native
checkpoint; they are now recorded in the completed 16-scene 1440p
[run](real-view/run.json), [results](real-view/RESULTS.md),
[data audit](INDEPENDENT-AUDIT.md) and [ordinary handoff](ordinary-handoff.json).
Actual Iris reports available/restored binding and matching main/alt C0/C4
RGBA32F at 2560x1440, C5/C8 RGBA16F at 2560x1440 and C6/C7 RGBA16F at 1024x512.
This initialization snapshot does not read HDR pixels or measure Iris energy.

All 16 captures are focused and active without fallback. The 14 overworld/water/
cave/glass 5-second samples average 126.5–196.9 FPS; 14,909 total intervals have
worst 10.601779 ms. These short observations do not guarantee an FPS floor or new
chunk traversal performance. The [actual-image review](../../docs/reviews/codex-v0.6-visual-audit.md)
confirms persistent cyan/jagged shores; motion/wakes are not accepted by stills.

Normal options are byte-restored, benchmark JAR/marker disabled, and a fresh
normal-account 0.6/physics 0.2.0 launch is paused. Saved TEST checks independently
confirm 390 reserved cells AIR and no ownership journal before/after stop. TEST
Save/Quit nevertheless stalled and required scoped termination; this is not a
clean exit or a shutdown fix. Whole-world/entity integrity is not claimed.

The ordinary world was saved through its normal UI with all-dimensions-saved
logs, and a private recoverable world/settings snapshot retained in `build/`.
No ordinary-world camera/time/terrain automation was used. Synthetic fixture
operations remain exact-UUID guarded.

## Still required by the full goal

Natural shoreline/cyan appearance remains unaccepted after the actual-image
review; temporal refraction/highlights and true rowing/contact waves require
motion review. Coherent spatial cloud shade and
cloud shape remain open. General underwater radiance/etendue, water membership,
arbitrary wet receiver normals/bent shadows and depth-resolved scattering are
not solved by this slice. Preserve the physical Snell window rather than
removing correct curvature to imitate an undistorted air camera.
