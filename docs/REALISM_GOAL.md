# Water and sunlight realism goal

Active user goal, begun 2026-10-02. The user wants convincing realistic water and
sunlight, including reproducible physical phenomena where useful, on this RTX
3080 Ti. A dedicated client Mod is allowed. The original60-FPS floor was relaxed:
visual quality is the priority, with honest actual Minecraft timing evidence.
The instruction to continue toward the goal is not satisfied by calling the
existing prototype finished or by passing only its existing tests.

## Current authoritative baseline

The currently installed, selected and ordinary-runtime verified experimental
pack is 0.5.0, ZIP SHA-256
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
the user's ordinary-account world runs0.5 and is paused. This runtime handoff
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
instrumented TEST-client shutdown stall remains an instrumentation defect, not
claimed fixed. Continue controlled shore optics diagnosis, natural motion,
coherent spatial cloud shade and calibrated sunlight. Cloud/light and other
full-goal requirements remain open.

## Execution sequence

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
