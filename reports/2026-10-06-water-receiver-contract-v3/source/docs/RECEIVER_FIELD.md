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

The adapter's new registry signatures were checked against the local pinned
1.21.1 intermediary bytecode. `javac` succeeds, but reflection in the running
game and rendering integration have not been tested. Do not install it as a
qualified release based on CPU tests.

CPU verification:

```sh
rtk proxy bash tools/test-receiver-field.sh
rtk proxy python3 tools/water_receiver_saved_replay.py --out reports/2026-10-06-water-receiver-contract-NEW
```

The replay output must not already exist. It independently decodes immutable
closed TEST terrain and checks16 actual original-MAIN refracted rays plus16
camera rays against the new Java implementation. This is saved-world CPU
evidence, not a new Minecraft/GPU run. See the v3 report and its remaining gates.
