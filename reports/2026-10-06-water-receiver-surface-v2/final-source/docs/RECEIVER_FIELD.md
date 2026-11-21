# Opaque receiver geometry candidate (not enabled)

`ReceiverField` is a pure, bounded, immutable geometry contract for the optional
read-only client bridge. It supplements—not replaces—the existing bathymetry
columns. Bathymetry cannot describe stepped first walls or camera-occluded beds.

`capture(World, Bounds)` copies at most65,536 cells, with each dimension1..64.
The caller must run on the world owner thread without concurrent world changes;
this is a synchronous prototype, **not** a per-frame update budget or cache.
Unloaded columns and out-of-build-height cells remain unknown without voxel reads.
`LoadedReceiverWorld` uses the existing retained `getChunk(FULL,false)` boundary.
No missing chunk generation, block writes, commands, Mixin registration, Iris
sampler registration, GL allocation or renderer scheduling is introduced here.

`Snapshot.firstHit(origin, unitDirection, maxMetres)` returns the first supported
opaque voxel, block registry identity, entry point/distance and entry normal.
Travel is bounded to48m. Unknown, unsupported, out-of-window, inside-solid and
ambiguous edge/corner/parallel-boundary cases are explicit non-hit statuses.
It must never search through those cells for a farther visually convenient bed.
Snapshots retain no chunk references and do not follow later world mutations.

The initial exact vanilla full-cube subset additionally requires empty fluid and
the pinned full/solid predicates. Transparent, partial, aquatic-cutout, modded
and unqualified blocks are unsupported. Pure vanilla water is traversable for
opaque geometry only: entered-water-cell count does **not** establish a continuous
water body, actual partial-fluid volume or a Beer attenuation path. Air can also
be traversed, so the geometric travel must not be assumed entirely underwater.

`HIT` means **geometry readiness only**. A registry name is not an atlas UV,
face material, tint, lighting, radiance or appearance-readiness proof. There is
intentionally no guessed sand color, screen-RGB proxy or shader hit promotion.
Actual vanilla appearance extraction, per-frame coherent snapshot lifetime,
bounded scheduling, sliced2D encoding/upload, dynamic Iris sampler assignment,
GL-state restoration and production optical joining remain required work.

At the initial geometry-only checkpoint the adapter's new registry signatures
were checked against the local pinned1.21.1 intermediary bytecode and `javac`.
The later actual-face probe below validates the loaded geometry/face reflection
boundary for its16 requested records, not a scheduled world snapshot or renderer
integration. Do not install this as a qualified release based on CPU tests.

CPU verification:

```sh
rtk proxy bash tools/test-receiver-field.sh
rtk proxy python3 tools/water_receiver_saved_replay.py --out reports/2026-10-06-water-receiver-contract-NEW
```

The replay output must not already exist. It independently decodes immutable
closed TEST terrain and checks16 actual original-MAIN refracted rays plus16
camera rays against the new Java implementation. This is saved-world CPU
evidence, not a new Minecraft/GPU run. See the v3 report and its remaining gates.

## Actual face input decoder and pinned adapter (still not enabled)

`ReceiverFace.decode` copies one actual opaque vanilla32-int quad into an
immutable face descriptor: axis/sign, atlas/sprite/UV bounds, an affine world-face
UV map, uniform unshaded vertex color, separate raw tint, shade flag, and raw
sky/block light plus the actual render-view brightness. Unsupported vertex
layouts, non-unit/partial faces, opposite winding, extra geometry, non-affine or
degenerate UV, nonfinite values, gradient/transparent vertex colors stay unready.
No guessed sand color or material radiance is produced.

`LoadedReceiverFaces.faceAt` requires the supported opaque geometry predicate and
already-loaded columns; obtains the block's actual rendering seed/model/face
quad, resetting the seed as the pinned caller does; rejects additional unculled
or multiple face quads. Tint blending additionally requires the conservative
maximum7-block surrounding columns already loaded. Adjacent-column raw light
reads remain inside build height. No command, world write, GL call, image access,
cache scheduler, sampler registration or shaded RGB calculation is added.

The [actual face evidence](../reports/2026-10-06-water-receiver-faces/README.md)
proves16 selected sand records (14 unique cell-faces, including UP/EAST/WEST)
through real Iris1.8.8/MC1.21.1 on RTX3080Ti. The original normal shader and
physics0.2 were unchanged; a standalone guarded TEST-only observer was removed
after clean exit. This includes the previously saved eight camera-hidden first
receivers, but does not assert saved/live geometry at the same fragment/frame.

Face-input readiness is not source readiness. The probe captured frame1, so
lighting warmup/stability is not proved. `vanillaBrightness` is the actual
MC render-view return value in the Iris/Sodium context (all1.0 here), not proof
of unmodified vanilla face shading or a physical lighting model. Raw light is
unsmoothed; there is no AO/per-vertex irradiance, actual texture pixel readback,
atlas epoch/reload coherence, CPU/GPU radiance convention, or water renderer
source upload yet. These must be qualified before renderer/source promotion.

The [handoff correction](../reports/2026-10-06-water-receiver-faces-handoff-addendum/README.md)
supersedes the first packet's invalid final-pause assertion without changing its
actual face records or producer. The corrected actual menu is15:36:17; the
original named pause image was gameplay and is preserved as rejected evidence.

```sh
rtk proxy bash tools/test-receiver-face.sh
rtk proxy python3 tools/test_water_receiver_faces_audit.py
```

## Actual static opaque sprite input (not renderer-enabled)

`ReceiverTexture.capture` owns copied, bounded256x256 static opaque mip0 ABGR
pixels. Sampling uses the decoded affine face UV and explicit top-first RGBA
conversion; it rejects wrong sprite identity or out-of-sprite UV. Animated,
nonopaque or unsupported shapes remain unready, not guessed colors.
`LoadedReceiverTexture` reads the actual pinned SpriteContents/NativeImage on
the render thread, never mutating or closing asset images. `materialAt` obtains
the face and texture from the same actual quad/sprite invocation. That one-shot
association is not a resource reload epoch, terrain snapshot scheduler or GPU
source lifetime proof.

The [actual texture packet](../reports/2026-10-06-water-receiver-texture/README.md)
qualifies48 warmed actual face observations and240 sparse sample checks against
independent JDK ImageIO decoding of the local stock sand PNG. Actual known-image
channel/copy-ownership controls pass. The three records are equal, including
raw light, but general temporal stability is not inferred. Native CPU nearest
mip0 pixels are not actual GPU atlas/mip filtering or source radiance. Sodium
AO/smoothed light, shared dry lighting, direct-Sun attribution, coherent bounded
geometry/material capture, Iris upload and production optical joining remain
required before shipping or claiming the two original-MAIN REDs corrected.

```sh
rtk proxy bash tools/test-receiver-texture.sh
rtk proxy python3 tools/test_water_receiver_texture_audit.py
```

## Exact first-face CPU material association (not renderer-enabled)

`ReceiverSurface.capture(geometry, stamp, surfaces)` owns a sparse catalog of
up to4096 unique cell/face owners and1048576 distinct retained texels. Existing
immutable textures can be shared; ambiguous duplicate ownership is rejected.
`firstSample(stamp, origin, direction, metres)` returns raw `PIXEL` only from
the first opaque cell's own block identity and entry normal. Missing/unready
first faces cannot borrow a farther color. All non-HIT geometry stays geometry
only. Different world/dimension/frame/atlas tokens return STALE, with no pixels.

The stamp is a caller contract, not a proved live epoch or capture scheduler.
It cannot by itself establish that saved geometry and live atlas/light data
were captured together, or survive aliased frame/revision counters. `PIXEL`
means nearest CPU input only, not filtered albedo, light, radiance or readiness
to promote a shader hit. Actual runtime capture/lighting/GPU joining is pending.

The [surface replay](../reports/2026-10-06-water-receiver-surface-v2/README.md)
uses the sealed saved-field and original16 refracted rays, later actual face
metadata and independently decoded full-digest matching stock sand texture.
All16 first-object/normal/UV pixel expectations match offline, including eight
previously hidden requests. The original water-MAIN radiance REDs remain open.

```sh
rtk proxy bash tools/test-receiver-surface.sh
rtk proxy python3 tools/test_water_receiver_surface_replay.py
```
