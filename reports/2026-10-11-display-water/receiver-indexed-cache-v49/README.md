# Indexed voxel cache v49 — actual improvement, goal still unachieved

The five per-cell phase caches now index a bounded padded voxel array instead
of allocating Top coordinate keys and hash nodes. The live constructor receives
the exact capture window; padding is two cells in X/Z and three in Y. Queries
outside it reject before a backend read. Epoch/thread ownership, unsupported
geometry handling, source shading and full fresh validation remain unchanged.
Chunk-loaded caching is unchanged and is not claimed optimized here.

CPU tests verify all 347802 cells of the actual padded 91×42×91 extent, repeated
queries without rereads, clearing and changing every value for validation,
six-side/extreme-coordinate extent rejection before backend access, exact signed
coordinates, missing/false values and thread/closed guards. Typed geometry,
source-volume and run-source/radiance/publication tests also pass. Mod v55 built,
SHA256 `0e3a36113c29f54c3bbccb2ff6d7a22e900903f702e12731f205dff54bd4bba9`.

Actual isolated Minecraft/NVIDIA, 1600×800, same guarded disposable world,
static/moving scenes, five-second warmup and 20-second sample as v48:

| Scene | v48 mean FPS | v49 mean FPS | v48 p99 ms | v49 p99 ms |
| --- | ---: | ---: | ---: | ---: |
| Static upward | 0.941689 | 1.231617 | 1352.110 | 1174.552 |
| Moving upward | 0.969615 | 1.313027 | 1208.143 | 897.252 |

The single paired run observes 31–35% higher mean FPS, with 24/26 measured
intervals versus 19/19. It does not establish repeatability or arbitrary-world
performance, and approximately 1.3 FPS is still unsuitable for normal use.

Actual frame-60 receipt matches v48's window, 55983 records, 6748 sources,
6777 mesh captures, 60 section copies and 600146 geometry reads. Producer wall
time is 780.365 ms (v48: 927.984). Collection is 236.876 ms, shading 270.381 ms,
fresh validation 257.139 ms and packing 4.804 ms. Nested meshing is 250.579 ms,
source draw/readback/handling 13.983 ms. These are wall measurements, not exact
independent GPU timings. Geometry reads were not removed to obtain speedup.
The frame-60 draw verifies ready=2, runMode=1, runCount and all six bindings.

Both scenarios completed, auto-quit and owned launcher exit zero; Java stopped.
Native-motion audit verified 50 PNGs. Static frame-023 was viewed: Sun visible,
but the sky-window distortion and dark polygonal exterior remain. Only this
still was reviewed, not the full moving sequence or phase-matched equivalence.
Normal config/Mods restored exactly and ordinary-save hashes remain unchanged,
without save rollback. No normal-runtime adoption or visual completion claimed.

Remaining producer work is roughly split between collection/validation and
private source meshing. Future optimization must preserve first-object and
paired-light ownership rather than omit unknown cells, fabricate floor light,
reuse stale state across frames, or shrink the optical field back to its old
coverage. The full Sun/underwater appearance and performance objective stays open.
