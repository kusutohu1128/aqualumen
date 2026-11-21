# Physics bridge 0.3.0 candidate

Client-only, read-only Minecraft 1.21.1 / Iris 1.8.8 bridge. Existing 0.2.0 contact/ripple interface is retained. This candidate adds a local water-depth texture; it does not simulate fluid conservation, generate chunks, modify blocks or issue game commands.

## Bathymetry interface

- `sampler2D aqualumenBathymetry`: 64×64 RGBA32F, nearest/clamp, no mipmaps.
- `vec4 aqualumenBathymetryGrid`: integer world-anchored origin X/Z **relative to the current unshifted camera**, 64m span, undisturbed reference surface Y relative to camera Y.
- `int aqualumenBathymetryReady`: at least one valid column exists in the current snapshot. This is not a full-window completeness or freshness flag.
- Texel `(i,j)` describes block column `(originX+i,originZ+j)`; its spatial sample center is `(originX+i+0.5,originZ+j+0.5)`.
- RGBA = `(depthMetres, actualUndisturbedSurfaceRelativeToCameraY, validity, 0)`; invalid texels are all zero. Surface height comes from the top fluid's intrinsic height, not displaced shader waves. Depth ends at the full-solid floor's top face.

The shader must independently reject out-of-window coordinates, invalid neighbours and incompatible actual mean-surface heights. A valid column is not proof that another water body is connected horizontally to it. The Mod accepts only a continuous vertical water column whose top is within 0.12m of the selected reference seed. Bathymetry does not depend on moving contacts or their 10-second active timer: an Overworld/world identity and finite seed are sufficient to attempt bounded scans, but `ready` still requires actual confirmed columns. The inherited default seed 63 is not asserted to be a real water surface. Other pond elevations need a nearby Contacts surface probe first; arbitrary visible/distant pools are not searched. A matching column may contain empty-collision aquatic vegetation; waterlogged partial/full collision cells, non-full/air floors, uncertain heights and columns deeper than the bounded 32-cell scan are unknown. Full-solid floors require empty fluid, a full unit-cube collision shape and Minecraft's solid-block predicate; this deliberately rejects some transparent floors.

## Bounds and lifetime

16 column scans per Iris frame, at most 40 voxel reads per scan, bounded 4096-column cache. New columns fill camera-centre-first, with a fair rolling refresh. Filling an entirely new window requires about 341 frames; a fully populated stationary window refreshes in at most 256 frames. Changed blocks are therefore **not immediately fresh**. Known columns are invalidated immediately when their client chunk is no longer present. World identity, reference plane change over 0.12m, pack reload and origin teleport over 16m invalidate the cache. Small recentering preserves world-anchored overlap.

The Minecraft adapter uses the retained chunk returned by `ClientChunkManager.getChunk(FULL,false)`, never the misleading `ClientWorld.isChunkLoaded` method (which returns true unconditionally in this pinned version). Per-frame chunk lookups are memoized (at most 25 chunks for the 64m window); voxel reads never fall through ordinary World getters. Dynamic shape predicates use the retained chunk as their BlockView and uncertain cases are conservative unknowns. No chunk references survive into the next frame.

Iris assigns the named dynamic sampler's texture unit. The supplier establishes the same frame snapshot before Sodium's sampler-before-uniform update order. A program registration/reload occurring mid-frame defers invalidation to the next frame. Upload runs only on the render thread and restores the prior active texture unit, 2D binding, unpack-buffer binding and pixel-unpack state. A single 64KiB texture allocation is reused across pack/world changes; no per-reload texture accumulation or explicit disposal hook. Runtime reflection/upload failure disables bathymetry rather than fabricating depth.

## CPU verification / build

```sh
bash tools/test-physics-mod.sh
bash tools/build-physics-mod.sh
```

The test fake implements only the external voxel boundary, not the extraction/cache internals. Tests cover real source-fluid 8/9 heights, confirmed floor depth, unloaded/no-read boundary, broken/partial/waterlogged/deep/nonfinite columns, plane mismatch, bounded fill/refresh, immutable snapshots and world/plane/teleport/unload invalidation. Intentional first failures are saved in `build/bathymetry-column-red.log` and `build/bathymetry-cache-red.log`; passing output in `build/bathymetry-cpu-green.log`.

The build emits `dist/aqualumen-physics-0.3.0.jar` without installation or overwriting `0.2.0`. Compilation and pinned API bytecode inspection do **not** prove live Mixin injection, actual Iris sampler binding/format, GL-state restoration or natural-coast quality. Those require parent-coordinated game/GPU acceptance after shader integration.

The existing 1Hz diagnostic `config/aqualumen-physics-status.json` gains a `bathymetry` object with ready/known/scanned counts, the snapshot frame, CPU update milliseconds, texture ID, issued upload calls and failure state. It may describe the preceding frame, which is explicitly identified. Upload-call counts do not prove GL-format/binding acceptance; CPU update time is not GPU or Minecraft-frame timing.
