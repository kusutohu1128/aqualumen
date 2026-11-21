# Natural-shore optical provenance checkpoint

This is diagnosis, **not an accepted shoreline fix or a new visual release**.
The ordinary-play pack remains0.6.0/physics0.2.0. Shipping water source hashes
remain FSH `231546b85e2317ba11d458b8033cca83301d779c8e92121f0545cd6805062f87`
and VSH `ad5f0ad33bdc9df04f5c6d0a18bbd87fd1f16442a2b46d836ea79a481451e219`.

## Actual three-panel-pair observations

The three explicitly named [captures](captures/) run the original production
water-main calculation and append diagnostic MRT stores. Optical/geometry r1
and transport r2 all completed actual Minecraft/Iris coast-day capture without
fallback. See their immutable run, scene, completion, PNG, raw CSV and physics
records. The opt-in world is exactV2 UUID
`b22dbccb-2970-41e6-847f-f183b1ec923d`, vanilla noise seed308060, one local TEST
player. Absolute camera is `(-191.5,65.71999988555908,320.5)`, yaw0/pitch9.

These are1600×900/cap120/VSyncOFF,12/6 chunks,10s warmup+5s observations.
They are **not the2560×1440 release performance test**, FPS floors, motion
acceptance or matched-pack timing A/B. The strict reporter was not weakened.
The independent [audit](audit.py) and [results](smoke-audit.json) cover only
the three named captures. Dynamic wave/contact/cloud phases were not frozen.

Main findings from the actual images:

- Strong cyan/mint water is already in the weighted transmission panel.
  Reflection mainly supplies the gray reflective ribbons, not the broad cyan.
- Broad cyan occurs where the known-column flag is set, so missing local depth
  alone does not explain it. The optical-normal panel is broadly continuous.
- Dark jagged regions covary with reduced hit confidence/proxy selection.
  This does not prove a false edge: real stepped geometry and visibility still
  need to be distinguished from an incorrect source handoff.
- Transport r2 shows largely yellow/beige sand in both the raw returned-UV C4
  panel and original-UV C4, but blue-green weighted transmission. Colored
  outgoing absorption is therefore an important causal path. Cyan exists for
  both accepted receiver-kind1 and proxy-kind0 samples.

The scatter×10 panel is an **incomplete estimate**, excluding the alternative
proxy-scatter contribution in the confidence mixture. It cannot establish zero
scattering or a full energy budget. Raw returned-UV C4 is before incident-Sun
correction and is also populated for the kind0 fallback; it is not exclusively
accepted-hit color. Diagnostic components precede GGX/foam/air, whereas the
original panel is post-composite and bypasses the original final five-tap AA.
They are not a complete additive decomposition of the final displayed image.

R1 panels used interpolated texture sampling. R2 uses integer `texelFetch`;
1600 pixels is not divisible by3, so nominal panel-to-panel corresponding
pixels can differ by1–2 original texels. PNG path estimates have approximately
0.188m/byte quantization. They are not calibrated full-float reads. Examples
around4–9m narrow the next query but do not prove those distances wrong.

## Saved terrain changes the interpretation

The read-only [saved-shore profile](saved-shore-profile.json) confirms that this
coast is shallow only at the camera site. Along centerX−192, the sandy bed drops
from topY62 atZ316–321 toY58 atZ328, Y57 atZ329–330 andY56 atZ331–341. The mean
surfaceY62.888889 gives approximately0.889,4.889,5.889 and6.889m water depths.
Further ahead it becomes deeper. Cave water under land was excluded.

Consequently the site's `water_depth_blocks=1` is **not a proof that all visible
water is one block deep**, and4–9m optical paths can be plausible. The fixed
absorption coefficients are chosen appearance parameters, not measured seawater.
At9.4m the outgoing RGB transmission is approximately `(0.049,0.450,0.720)`.
Do not call a trace-distance bug proven or change the coefficients solely to
hide the color. A same-frame source-pixel→surface→ray→receiver join is still
required, followed by incident-light/source separation if geometry is correct.

## Tool failures and bounded checks

The first optical diagnostic pack failed in real Iris: a dynamic `gl_FragData`
index passed native compatibility compilation but the Sodium shader transformer
left it unrewritten. The original [failed pack](packs/Aqualumen-ShoreProbe-optical.zip)
is preserved. Literal output indices in r1/r2 compile and activate in Minecraft.
This is an observation-tool RED/GREEN, not a rendering-defect fix.

Packaging tests check original water-main text recovery and protect shipping
source/dist trees and existing output files. They do not prove actual floating
pixel neutrality. [Original packaging checks](packaging-tests.log) and
[world-probe checks](packaging-tests-world-green.log) are separate from visual
acceptance. The archived source reflects the corrected legend; the older
captured transport ZIP carries its original legend plus transport override.
Preserved ZIPs, not a later rebuild's metadata, identify the captures.

## Lifecycle limitations

After the three r1/r2 observations, the TEST GUI Save/Quit stalled; no final
`All dimensions are saved` or clean-exit marker was observed. A first diagnostic
attach incorrectly used namespacePID27 (the render-thread TID); the corrected
Java PID26 produced a private thread dump. Only the identified TEST Java and
its own launcher were then terminated after cleanup checks. The two persisted
[pre-exit](lifecycle/test-stored-air-pre-exit.json) and
[post-exit](lifecycle/test-stored-air-post-exit.json) audits establish390 approved
cells AIR and no ownership journal, not complete world/entity integrity.
This is not a shutdown fix. Private save backups and unfiltered logs are not
published. Normal configuration was restored, and the full ordinary save equaled
the fresh post-user-play backup before its subsequent0.6 relaunch. Ordinary
game writes naturally resume after relaunch; old pre-user-play backups were not
restored over newer play.

## Next evidence, not yet acceptance

A world-coordinate MRT probe and typed actual-FINAL-sampler observer now have
their own [real-runtime checkpoint](../2026-10-02-shore-world-r3/README.md).
Their CPU/packaging checks remain distinct from that actual GL readback and its
conditional saved-terrain join. They do not establish full observational
neutrality, physical receiver visibility or an accepted natural-shore fix.
The complete water/sunlight goal remains active: natural shores, moving
reflections/highlights/wakes and spatially coherent cloud illumination remain
unaccepted.
