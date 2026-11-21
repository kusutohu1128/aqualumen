# Typed geometry v48 — actual API compatibility, insufficient performance

Actual isolated Minecraft/NVIDIA, 1600×800, UUID-guarded AqualumenNaturalV2,
same static/moving scenes and five-second warmup/20-second sample as v47.
Mod v54 changes per-cell geometry dispatch from reflection varargs to exact
typed method handles. The same pinned public APIs and qualification are used.
No recording instrumentation was active during this comparison.

| Scene | v47 mean FPS | v48 mean FPS | v47 p99 ms | v48 p99 ms |
| --- | ---: | ---: | ---: | ---: |
| Static upward | 0.849654 | 0.941689 | 1462.075 | 1352.110 |
| Moving upward | 0.880839 | 0.969615 | 1217.085 | 1208.143 |

Each v48 sample has 19 measured frame intervals, versus 17 in v47. The single
paired run observes about 10–11% higher mean FPS, not general/repeated performance
acceptance. Approximately one FPS is still unsuitable for ordinary play.

Actual frame-60 source receipt retains the same v47 window, 55983 records,
6748 sources, 6777 mesh captures, 60 section copies and 600146 geometry reads.
Producer wall time is 927.984 ms (v47: 1054.703 ms). Collection is 342.041 ms,
shading 244.500 ms, fresh validation 330.651 ms and packing 3.097 ms. Nested
meshing is 217.424 ms and source draw/readback/handling 22.928 ms. These are
CPU wall receipts, not independently measured GPU timings.

The actual owned API resolved and produced the field rather than failing to
unavailable. Both frame-3 and frame-60 draw receipts verify ready=2, runMode=1,
runCount and all six sampler bindings. This proves current runtime routing,
not arbitrary Minecraft versions or full-world rendering correctness.

Both scenarios completed and auto-quit; launcher exited zero and Java stopped.
Native-motion audit verified 38 PNGs. Static frame-018 was viewed: Sun visible,
distorted sky-window perimeter and dark polygonal exterior still present.
No full motion acceptance or pixelwise phase-matched comparison is claimed.
Normal config/Mods restored exactly; ordinary saves unchanged without rollback.

Next bottleneck remains collection/fresh validation plus source meshing. A
bounded coordinate-indexed phase cache can remove Top keys/hash nodes while
retaining exact coordinate ownership, thread/closed guards and clearing all
values before fresh validation. Its padded extent must cover actual neighbor
queries, reject out-of-extent access before reading the world, and be tested
against every coordinate and changed-value/owner/close negatives before live
integration. Do not trade fewer fresh reads for apparent speed or remove
unknown/unsupported geometry. Appearance, Sun transport and performance goals
remain open; this checkpoint is not a release or normal-runtime adoption.
