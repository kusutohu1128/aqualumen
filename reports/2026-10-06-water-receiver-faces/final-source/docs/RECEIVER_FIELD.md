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

```sh
rtk proxy bash tools/test-receiver-face.sh
rtk proxy python3 tools/test_water_receiver_faces_audit.py
```
