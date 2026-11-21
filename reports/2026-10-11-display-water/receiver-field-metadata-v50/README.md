# Field metadata v50 — faster source capture, appearance still unaccepted

ReceiverMemberCache now caches Field metadata by owner class/name, preserves
nearest-declared/inherited lookup and shares its bounded capacity with methods
and constructors. ReceiverSodiumIntake still calls Field.get on the current
renderer/slice each time; it does not cache mutable positions, vertices, world
state or shaded values. Exhaustion fails through the reflection-unavailable
boundary. CPU tests cover inheritance, hidden fields, changed values, different
objects, missing fields and shared bounds, plus owned Sodium scope and run-source
controls. Mod v56 SHA256:
`caf8ff609a7ee90938e0010c1284cb73565816ba813c758d1dac94362419415d`.

Actual Minecraft/NVIDIA, isolated UUID-guarded world, 1600×800, same static/moving
views and five-second warmup/20-second sample as v49, without JFR:

| Scene | v49 mean FPS | v50 mean FPS | v49 p99 ms | v50 p99 ms |
| --- | ---: | ---: | ---: | ---: |
| Static upward | 1.231617 | 1.488009 | 1174.552 | 703.053 |
| Moving upward | 1.313027 | 1.525388 | 897.252 | 697.121 |

The single paired run observes 16–21% higher mean FPS, with 29/30 measured
intervals instead of 24/26. It is still unsuitable for ordinary play; this is
not a repeated/general performance claim or release acceptance.

At frame 120 the actual field retains 55983 records, 6748 sources, 6777 mesh
captures, 60 section copies and 600146 geometry reads. Producer wall time is
603.182 ms: collection 222.909 ms, shading 146.749 ms, fresh validation 222.660
ms and packing 3.400 ms. Nested meshing 122.884 ms and source draw/readback/handling
20.692 ms are not independent GPU timings. Fresh reads were not omitted.

Both scenarios completed and auto-quit; owned launcher exit zero, no Java left.
Native-motion audit verified 59 PNGs. Static frame-028 was viewed: Sun remains
visible, with a distorted sky-window perimeter and dark exterior still present.
Only this still was reviewed, not complete motion acceptance. Exact normal
config/Mods and unchanged ordinary-save hashes were restored without rollback.

The earlier narrow-field diagnostic cannot establish today's dominant optical
rejection after widening the field. A fresh wide-field diagnostic should
distinguish field exit, unknown/interface failure, range and missing/wrong-face
source. Code inspection confirms current producer sources are UP-only and the
shader requires the sampled source normal to equal the first opaque hit normal.
This is a possible vertical-face coverage limitation, not proof that it causes
the whole dark exterior. Do not fix it by borrowing another face's radiance or
forcing misses into sky/floor hits.

An attempted bytecode inspection of `build/intermediary-1.21.1.jar` found no
WorldChunk class. It is not evidence for replacing chunk-fluid reads with a
block-state shortcut; obtain the actual mapped runtime class before that change.
Full Sun transport, underwater-window appearance and performance goals remain open.
