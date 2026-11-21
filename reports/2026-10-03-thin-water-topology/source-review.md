# Thin-water top/bottom topology review

Codex independent CPU/source review, 2026-10-03. No GPU, Minecraft input, Mod,
network, shader change, or frozen-report update. The conclusions below separate
bytecode-derived topology, a CPU arithmetic model, and still-required GPU tests.

## Recommendation

A negative-known VS admission condition such as
`fract(undisplacedAbsoluteY) > 0.01` is proportionate for the pinned vanilla
Sodium/Iris path. It separates bottom vertices from actual top vertices without
shrinking the shared `0.12` bathymetry height tolerance. Require genuine native
RED/GREEN before adopting it. Preserve the positive-top branch and all existing
Fresnel, TIR, transmission, unknown-weight and shared-column contracts.

This is not a general fluid-meshing guarantee for arbitrary mods, huge custom
vertical coordinates or uncaptured nonrigid view transforms. Test the actual
production VS/FS, not a standalone fractional-Y function.

## Fresh source identity

Installed Lab Sodium 0.6.9+mc1.21.1:
`411c4c03167066f0e2e61ba17793b4be13ddd73de5b677c6d402f1d8f4262ac2`.
Installed Iris 1.8.8+mc1.21.1:
`b5ad39a6cb113ca0a1765f06689f9f4b29ccd0c81247de90b06c42f5da1092f5`.
Remapped Minecraft 1.21.1 client:
`ffcab71074c28fac8521c30eb6e11f10333f76f3e173f7401aef5cfb26054563`.
VS/FS/helper hashes at the initial source inspection, respectively:

```text
fa5dc7aa41e83bb99837b442a4d8abc0eb2e05568fe25360690f02b01d5e1d93
8dfae28a5a98d5c9be4a0e39488cdfe66a01440d2123fd786e83e3e3fcfc0b18
0f663ff635e5e43628dab8d5c3b69f1b3f1e7d19aa9242f9d85c1131dbafd527
```

That VS treats any negative horizontal face as a top when the helper
returns known. The helper accepts four valid finite depths with
`abs(surface - undisplacedMeanY) <= .12`. A thin bottom `.001` below a surface
`1/9` therefore passes that height check: separation `.110111... < .12`.
The FS promotes the negative face only after the interpolated unknown weight
equals zero. Leaving a rejected bottom's VS weight at one makes that existing
FS gate reject it; no new optical-side special case is required. The subsequently
inspected root patch adds the proposed discriminator only to negative VS
admission; VS SHA256 is now
`16554f88edf3519481447f22f44b18a06c40881a27504b81e67b58efab266df0`.
FS and helper remain unchanged.

## Pinned vanilla visible-bottom counterexample

Thin water on a **slime-block floor** can supply a valid column and a rendered
bottom. This is a bytecode-derived possible input, not a live reproduced world.

- `class_2246` slime registration offsets 18158-18195 construct `class_2490`
  with `method_22488()` (noOcclusion), without a redstone-conductor override.
- `class_4970$class_2251.method_22488` sets `field_20721` false. The state exposes
  this as `method_26225` (canOcclude).
- Default `field_23182`, BootstrapMethods #3, invokes `method_26248`, which
  directly returns `state.method_26234` (full collision shape). Slime's classes
  `class_2490 -> class_2373 -> class_2248` do not alter collision shape. Default
  `class_4970.method_9530` returns the full cube, and `method_9549` returns that
  shape when collision is enabled.
- `LoadedWorld` accepts empty-fluid, non-air, collision-full and
  `method_26212` (redstone conductor) as its floor. Slime meets these source
  predicates; ordinary glass instead has an explicit conductor override.
- Sodium `BlockOcclusionCache.shouldDrawFullBlockFluidSide`: neighbor
  canOcclude=false returns true at offsets 164-173, unless earlier fluid-kind
  rejection applies. `FabricBlockAccess.shouldOccludeFluid` offsets 0-14 reject
  only the same fluid kind; a slime floor has empty fluid, not water.
- `DefaultFluidRenderer.isSideExposed` returns true at 100-101 for a neighbor
  with canOcclude=false. Therefore both independent bottom culling checks pass.

This is stronger than relying only on stale-cache/custom-block hypotheses.
Rolling bathymetry can also temporarily retain an old valid floor after edits;
do not use the map as an instantaneous topology discriminator.

## Heights, encoding and arithmetic scope

`DefaultFluidRenderer.render` offsets 447-458 use block-local `.001` for a visible
bottom; 1373-1426 assign that Y to every bottom vertex. Top offsets 546-572
subtract `.001` from the corner heights. `fluidCornerHeight` includes the
current positive cell and at most three neighbors; `modifyHeight` ignores
negative samples and assigns weight 1 below `.8`, weight 10 otherwise.
Minecraft `class_2741` LEVEL spans 1..8; flowing water
`class_3616$class_3617.method_15779` returns LEVEL, still water's `class_3618`
returns 8, and `class_3609.method_20784` divides the level by 9. A conservative
minimum top corner is therefore `1/36 - .001 = .026777...`. This is a stress
lower bound, not an attainable isolated corner: when both cardinal neighbors
are zero, Sodium omits the diagonal, giving the attainable isolated level-1
corner `1/27 - .001 = .036037...`. Dry neighbors may also make the map unknown;
a synthetic valid-map corner test is not proof of natural field availability.

Iris `XHFPTerrainVertex.quantizePosition` truncates float32
`((8 + p) / 32) * 1048576`, masked to 20 bits. `SodiumTransformer` decodes with
`32 / 2^20` and offset `-8`, then adds `u_RegionOffset` and local draw translation.
The quantization spacing is `1/32768`, well below the separation. Camera tracker
`updateShift/applyShift` changes X/Z only: Y is not rebased, and must be included
in arithmetic tests.

A CPU float32 sensitivity enumeration modeled that quantization, shader
region/draw additions, synthetic float32 rigid yaw/pitch matrices and their
transpose inverses, and restored absolute Y. It used block Y -64..319; camera Y
`[-63.95,-.05,.05,62.38899988555908,64.05,319.95]`; yaw 0..330 in 30-degree steps;
pitch -90..90 in 15-degree steps; relative X/Z each `[-192,0,192]`. Each shape
had 3,234,816 combinations and zero `.01` classification errors:

| Shape | Observed fractional-Y interval |
| --- | --- |
| bottom `.001` | `.00091552734375 .. .00103759765625` |
| top `1/9 - .001` | `.11004638671875 .. .11016845703125` |
| conservative corner `1/36 - .001` | `.02667236328125 .. .026824951171875` |
| source top `8/9 - .001` | `.8878173828125 .. .887939453125` |
| full top `1 - .001` | `.9989013671875 .. .999053955078125` |

Maximum modeled absolute-Y error was `.000105414497`. The actual saved camera
Y came from `reports/2026-10-02-underwater-reasons/before-near-reasons.json`.
The enumeration was CPU evidence, **not** actual Iris matrix capture/replay,
driver precision acceptance, exhaustive head-bob validation or live rendering.
Its temporary V8 implementation was not saved as an executable file. The exact
figures above are recorded sensitivity observations, not a reproducible
acceptance artifact; use the retained native controls below for that boundary.
At very large Y, float32 can lose `.001` and round a full top to an integer;
arbitrary mod heights are not justified by this normal-height model.

The pinned matrix producer path does not reveal a separate terrain/view-bob
matrix mismatch: Iris `MixinLevelRenderer.iris$setupPipeline` at HEAD stores
renderLevel's sixth argument by reference in `CapturedRenderingState` (offsets
7-12). Minecraft `class_761` forwards that same argument to translucent
`method_3251` (2231-2235 or 2366-2370). Sodium's `LevelRendererMixin` stores it as
`ChunkRenderMatrices.modelView`, and `DefaultChunkRenderer` uploads it at 50-53.
Iris's common inverse is derived from the captured matrix. This is a source
path check, not captured-matrix GPU arithmetic or third-party-mixin proof.

## Required neighboring GPU controls

Keep the thin-bottom RED's typed valid `1/9` column and pinned `.001` vertex
input. Add opposite-winding positive tops at thin `1/9`, conservative corner,
source and full heights, plus the retained deep known-top and unknown controls.
Do not require a result to be known merely because a point was named a top:
qualify actual raw helper result, contributing VS weights, finite outputs,
nonzero-wave sensitivity and STORE/C0 neutrality separately.

For the corner-min positive, camera 64.05 is above top 64.0267778. Use an
explicit below-interface camera such as 64.005 and an appropriately declared
near plane if testing the real underwater orientation; do not silently spoof
the normal/view relationship. Repeat translation controls at negative and
upper build heights. A sloped/mixed primitive may still reject the local field;
the new discriminator must not force it known or repair unrelated fallbacks.

The root's subsequently saved `build/thin-interface-native-red-v3-20261003/`
and `...green-v3.../THIN-SUMMARY.txt` were inspected without rerunning GL. Same
thin-bottom input changes from displacement `.0015725158`, weight 0, final
known/top 1 to zero displacement, weight 1, final known/top 0. Raw known remains
1, and STORE/repeat whole-C0 differences remain zero. This is an uploaded
classifier seam: that camera is above the bottom, and the rasterizer admits its
back side. It is not the ordinary visible-bottom viewpoint.

The saved `build/thin-interface-controls-green-v4-20261003/`
`TOP-CONTROL-SUMMARY.txt` has 25 passing opposite-winding controls: five top
heights (stress corner, attainable corner, thin, source, full) at block heights
[-64,-1,0,64,319], below-top camera block+.01 and fixture near .001. All use
byte-exact typed maps, raw known 1, known/top 1 on both windings, nonzero-wave
sensitivity and zero position/normal/C0 STORE differences. These bounded tests
support the new admission guard; they are not encoded live-mesh validation.

For a front-facing bottom seen from below in air, camera block-.05 has the right
normal/IOR orientation but lies **inside** its one-block slime floor. A plausible
ordinary below-floor viewpoint is block-1.05, looking through transparent
slime. `Contacts.surface` probes baseY +/-3 and does not stop at solid cells, so
it can still find this water plane from there. A native test without slime
geometry remains a classifier/orientation test, not a whole-scene photograph.

The subsequently saved `build/thin-interface-controls-green-v5-20261003/`
`AIR-BOTTOM-SUMMARY.txt` was also inspected read-only. Its five supplied
front-facing bottoms use eye block-1.05, air medium and GL_BACK culling ON at
[-64,-1,0,64,319]. All are GREEN with exact typed input, raw known 1, final
known/top 0, zero VS displacement/weight delta and whole-C0 differences, and
normal error at most `5.9604644775391e-08`. The same v5 directory retains all 25
GREEN opposite-winding tops, deep known top, deep true bottom, unknown backtop
and the original thin-bottom seam. The inspected VS and FS hashes still match
the guarded hashes above. This closes the additional supplied front-facing
classifier control; it does not reproduce the slime geometry or a live mesh.

## Read-only evidence selectors

Use task-specific jar-path variables pointing to the installed jars above:

```bash
javap -c -p -classpath "$sodium_review_jar" net.caffeinemc.mods.sodium.client.render.chunk.compile.pipeline.DefaultFluidRenderer
javap -c -p -classpath "$sodium_review_jar" net.caffeinemc.mods.sodium.client.render.chunk.compile.pipeline.BlockOcclusionCache
javap -c -p -classpath "$sodium_review_jar" net.caffeinemc.mods.sodium.fabric.block.FabricBlockAccess
javap -c -p -classpath "$minecraft_review_jar" net.minecraft.class_2246
javap -c -v -p -classpath "$minecraft_review_jar" 'net.minecraft.class_4970$class_2251'
javap -c -p -classpath "$minecraft_review_jar" net.minecraft.class_2490
javap -c -p -classpath "$minecraft_review_jar" net.minecraft.class_2373
javap -c -p -classpath "$minecraft_review_jar" net.minecraft.class_4970
javap -c -p -classpath "$iris_review_jar" net.irisshaders.iris.vertices.sodium.terrain.XHFPTerrainVertex
javap -c -p -classpath "$iris_review_jar" net.irisshaders.iris.pipeline.transform.transformer.SodiumTransformer
javap -c -p -classpath "$iris_review_jar" 'net.irisshaders.iris.uniforms.CameraUniforms$CameraPositionTracker'
```
