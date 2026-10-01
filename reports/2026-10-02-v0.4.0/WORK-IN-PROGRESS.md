# Aqualumen 0.4 water/light work in progress

This is a current progress checkpoint, **not** proof of full-goal completion.
The installed and selected experimental pack is 0.4.0, SHA-256
`5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069`;
the previous 0.3.3 archive and comparison data are preserved. Ordinary play was
saved and closed normally before the isolated work; normal settings restoration
and development-instrumentation disablement are still pending at handoff.
The full realistic-water/sunlight goal in
[`REALISM_GOAL.md`](../../docs/REALISM_GOAL.md) is not yet achieved.

## Reproduced first behavior and correction

The production water main previously refocused unchanged diffuse/block receiver
RGB according to an absent Sun's direction. The zero-direct-source test failed
with maximum RGB difference0.0289524. An opaque direct-Sun attachment and an
immutable pre-translucent snapshot now carry receiver-specific albedo, normal,
shadow, daylight and weather attribution. The same test gives0. A positive
red-only Sun control changes red0.0107598 and green/blue0, so focusing was not
simply disabled. Production terrain/deferred MRT positive and zero-Sun controls
match the snapshot and tolerate subsequent mutations of the producer buffer.

A second actual-main finite-shelf fixture exposed focusing on an unconfirmed
refracted receiver's original-UV proxy: RGB change0.000158489. Requiring a
confirmed receiver now gives0 while retaining the positive full-bed control.

All above are native NVIDIA RTX3080Ti OpenGL4.6 fixture results, **not**
Minecraft visual quality or frame-time measurements. The established underwater
main sky/Fresnel/TIR/opaque/cave/Sun/Moon/translated-eye controls pass.

## Subsequent vertical slices

The actual-main continuous-bed regression originally retains a blue jump
0.066329 across a depth perturbation approximately0.00004m. Fixed above-water
refinement plus separately transported hit/proxy radiance blending reduces the
preserved failing interval's change to0.00000570714; output changes shrink as
the physical perturbation shrinks. This proves that reproduced smooth-receiver
handoff, not all discrete bank topology or natural coast appearance.

Underwater composite zero-direct-source invariance separately failed with
RGB difference0.0769311 and now gives0. Its positive red-only C8 control still
focuses red0.0285025 with green/blue unchanged. Raw matched-depth/C8 pixel reads
retain positive focusing and reject nearer-layer behind-Sun leakage with both
NEAREST and LINEAR source samplers. Depth-write-free/coplanar translucency cannot
be identified by matching depth alone and remains a conservative limitation.

## Completed validation at this checkpoint

- The rejected foreground-bank positive/negative controls and final full native
  suite pass. See [native-final-check.txt](native-final-check.txt): RTX 3080 Ti,
  OpenGL 4.6, 11 graphics program pairs and retained production/physics controls.
  These are archived fixture results, not an arbitrary-world or Minecraft FPS
  guarantee.
- The active 0.4.0 pack completed 16 Minecraft/Iris scenes without recorded
  fallback: coast, river, ocean day/dusk/night/rain, underwater and three upward
  water views, moving view, scripted boat contact, cave, glass and Nether/End.
  Four paired 0.3.3 scenes are retained. Minecraft reports GL 3.2, distinct from
  the native harness's GL 4.6 context.
- The [independent exported-data audit](INDEPENDENT-AUDIT.md) confirms 20 strict
  PNGs and all 18,506 raw intervals (3,889 before / 14,617 after), recalculated
  metrics, archive/scene SHA identities and recorded poses/settings. Explicit
  eye/first-person/time controls are recorded for upward-water views; generic
  scenes do not export every eye/time/weather control.
- All candidate P99 values fit 16.667 ms, but dusk and night each have one slower
  interval; worst 21.775271 ms. The original 60-FPS floor was relaxed. The four A/B
  average FPS values are lower, and two pairs differ in capture focus, so the
  difference must not be attributed solely to the pack. Coast/river image pairs
  remain focused; the other 14 candidate captures are unfocused at capture time.
- Both runs report completed fixture cleanup. That does not establish normal
  options/marker/JAR restoration or disabled development instrumentation.

## Remaining observed limits

The natural shallow-water cyan and jagged/discrete shoreline appearance remain.
The corrected numerical handoff and Sun attribution address reproduced causal
fixtures, not every natural bank silhouette or full optical bottom illumination.
Cloud attenuation is still camera-global, cloud shapes remain approximate and
the visible Sun/direct-light energy convention is not yet calibrated.

Temporal video attempts were clipped rather than correctly framed full-view
evidence. Preserve those attempts, but do not use them to certify temporal
quality. Replacement capture/review is pending; video capture/encoding load
also makes such runs distinct from the saved performance samples.

## Still required

- Review correctly framed moving-camera/contact footage and retain matched
  natural-image controls; the 16-scene run alone does not resolve the cyan/jagged
  appearance or certify temporal stability.
- Continue the diagnosed water appearance and receiver-illumination work without
  cosmetic compensation for incorrect geometry paths.
- Restore ordinary play settings and disable development instrumentation.
- Continue cloud/sunlight coherence and audit every full-goal requirement.

Implementation/reviews in this slice are Codex work, not an external Claude call.
