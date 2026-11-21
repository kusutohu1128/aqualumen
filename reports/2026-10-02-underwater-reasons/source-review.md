# Independent source review: reversed water top

Codex read-only review, 2026-10-03. No build, OpenGL execution, Minecraft input,
or source modification was performed by this reviewer. Saved GPU results below
were read, not rerun. This note is the reviewer's only authored file.

Reviewed VS SHA256:
`fa5dc7aa41e83bb99837b442a4d8abc0eb2e05568fe25360690f02b01d5e1d93`.
Reviewed FS SHA256:
`8dfae28a5a98d5c9be4a0e39488cdfe66a01440d2123fd786e83e3e3fcfc0b18`.
Bathymetry helper SHA256:
`0f663ff635e5e43628dab8d5c3b69f1b3f1e7d19aa9242f9d85c1131dbafd527`.

## Bounded conclusion

No source blocker for the confirmed, same-height reversed-top correction. A
comparison to `build/underwater-reasons-084-v1-extracted/original/shaders/`
isolates the VS negative-horizontal-face admission and FS promotion after the
existing contributing-vertex gate. Positive-top displacement remains the same;
physical constants and trace/transport helpers are unchanged. Do not generalize
this to unchanged behavior on *all* negative faces viewed from air: their
corrected `upperSurface` classification can intentionally affect existing
above-water branches.

`before-near-reasons.json` has 16 water-qualified C9 samples with input normal Y
`-0.9999682903`, weight `0.9999999404`, raw known `1`, final known `0`. Actual
samplers C9/C10/C11 are scalar sampler2D, RGBA32F, 1600x900; the eleven recorded
GL state fields agree before/after. Inactive FINAL geometry uniforms mean this
readback alone is **not** complete geometry attribution.

Saved `backface-native-red/SUMMARY.txt` and `backface-native-green/SUMMARY.txt`
exercise original production VS/FS on one confirmed same plane. VS position
difference changes from `0.0567159653` to `0`, centre optical-normal difference
from `0.1452614814` to `0`; whole-C0 STORE/repeat differences are `0`. This proves
that bounded seam, not live Sodium meshing or natural-rim quality.

The saved negative controls cover a four-metre-separated bottom and an invalid
map top only. Both reject known/top classification. They do **not** prove the
guard safe for thin fluid, mixed triangles, every side, or every live world.
The VS still leaves unknown negative tops undisplaced, while positive unknown
tops retain their fallback waves. Mixed primitives reject local-column shading
through `waterUnknownWeight == 0`; front/back symmetry there remains incomplete.
Vertical normals with `abs(Y) <= .5` remain excluded.

## Thin-bottom boundary, not yet a reproduced natural defect

`localWaterColumn` permits `abs(surface - meanSurfaceY) <= .12`, positive depth
up to 128, and four valid texels. Thus a hypothetical negative bottom at local
Y `.001` under a valid `1/9`-high fluid column passes the height test:
`1/9 - .001 = .110111... < .12`. The current negative-face VS admission would
displace it and could permit FS promotion. The existing four-metre negative
cannot detect this. No thin-bottom GPU RED or live natural failure has been
established by this review.

Ordinary stone-floor topology often prevents this combination: `BathymetryField`
rejects a column whose first nonwater cell is not its model's full-solid floor;
Sodium omits an occluded bottom. The model's actual pinned floor predicate is
empty fluid, non-air, full collision shape, **redstone conductor**. In
`LoadedWorld`, `method_26234` is officially `isCollisionShapeFullBlock` and
`method_26212` is `isRedstoneConductor`, despite the local variable name `solid`.
Do not assert ordinary glass is a valid floor. Rolling cached columns are not
an instantaneous topology guarantee after block changes, and custom predicates
are not covered by the current tests.

## Primary bytecode evidence and a proportional next test

Installed Sodium 0.6.9+mc1.21.1 jar SHA256:
`411c4c03167066f0e2e61ba17793b4be13ddd73de5b677c6d402f1d8f4262ac2`.
Pinned remapped Minecraft jar SHA256:
`ffcab71074c28fac8521c30eb6e11f10333f76f3e173f7401aef5cfb26054563`.
Paths are the Lab instance's `minecraft/mods/sodium-fabric-0.6.9+mc1.21.1.jar`
and `.fabric/remappedJars/minecraft-1.21.1-0.19.5/client-intermediary.jar`.
Read-only reproduction selectors (supply these paths as task-specific variables):

```bash
javap -c -p -classpath "$sodium_review_jar" net.caffeinemc.mods.sodium.client.render.chunk.compile.pipeline.DefaultFluidRenderer
javap -c -p -classpath "$sodium_review_jar" net.caffeinemc.mods.sodium.client.render.chunk.compile.pipeline.BlockOcclusionCache
javap -c -p -classpath "$minecraft_review_jar" net.minecraft.class_3609
javap -c -p -classpath "$minecraft_review_jar" net.minecraft.class_2741
javap -c -p -classpath "$minecraft_review_jar" 'net.minecraft.class_3616$class_3617'
javap -c -p -classpath "$minecraft_review_jar" 'net.minecraft.class_3616$class_3618'
```

`DefaultFluidRenderer.render` offsets 447-458 set visible bottom local Y to
`.001`; 1373-1426 use it for all bottom vertices. Top offsets 546-572 subtract
`.001` from corner heights. Offsets 1270/1322 emit the same top with normal and
reversed winding. `fluidCornerHeight` combines the current positive water height
and at most three neighbors; `modifyHeight` ignores negative heights, uses
weight 1 below `.8` and weight 10 above it. Minecraft `class_2741` sets LEVEL
to 1..8; `method_15779` returns LEVEL for flowing water and constant 8 for still
water. `class_3609.method_20784` returns level/9. Therefore a conservative top
corner lower bound is `1/36 - .001 = .026777...`, separated from bottom `.001`.

Next: obtain genuine production-VS/FS GPU RED with a thin valid column and the
pinned bottom epsilon; retain positive reversed-top controls at the lowest
corner, source-height and full-height boundaries. Only then evaluate a local
negative-VS admission condition such as `fract(undisplacedAbsoluteY) > .01`.
Do not shrink the shared `.12` tolerance: it also accommodates legitimate
corner-averaged tops. Test negative/positive block heights, camera cancellation
and actual vertex encoding before treating the fractional-Y discriminator as
verified. At large float magnitudes `.001` can be lost; arbitrary world/mod
heights are not proven by this bytecode reasoning. Keep physical Fresnel, TIR,
Beer transport, positive fallback, shared tolerance and unknown gates unchanged.
