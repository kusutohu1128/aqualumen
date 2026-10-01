# Scripted boat-contact outliers

Accepted run: `natural-v2-final-zgc`, shader SHA-256 `be819e6bb54b94ad5306cd60f3b1e839894e656973d54179016bf0f6ca78e794`, RTX 3080 Ti, actual 2560×1440 framebuffer, 12 render / 6 simulation chunks, Generational ZGC with 2 GiB initial / 6 GiB maximum heap.

The 30-second boat scene contains 9,736 render-loop intervals. Two exceeded the 16.667 ms budget; both remain in the report. Mean 324.5 FPS, 1% low 124.7 FPS, P99 5.435 ms, worst 70.056 ms. It does not establish an absolute 60 FPS floor for this workload.

| Raw CSV frame (zero-based) | Interval ms | Cumulative interval end, seconds after sampling boundary |
|---|---:|---:|
| 3858 | 70.055848 | 11.777760 |
| 5229 | 35.184969 | 16.008997 |

Cumulative times were independently reconstructed by summing raw CSV nanoseconds. The first sampling-boundary interval is discarded by the recorder. Minecraft's log places sampling at 21:51:01 JST, but provides only whole-second precision.

The physics bridge was active and reported one contact in all 31 once-per-second/end-of-sample snapshots; 30 had nonzero force, maximum 8.0. The reset counter stayed at 5. This confirms real contact input, but sparse snapshots cannot identify either frame's CPU/GPU cause.

The matching local game log contains 3,203 vanilla boat `moved wrongly` warnings from 21:51:01 through 21:51:31 JST, counted by timestamp range plus the literal warning text. Whole-second bins contain 60–206 warnings. The mounted boat is translated by server teleport commands at 6 m/s, nominally 20 Hz: measurements include scripted movement, vanilla network corrections and logging, not just water rendering or normal player-controlled rowing. Warning frequency is observed; its share of frame delay was not profiled.

The process started at 21:41:06 JST according to `ps`. The preserved GC log (`natural-gc.log`) has a concurrent ZGC minor cycle at uptime 612.079–612.366 seconds, approximately around the second hitch. No contemporaneous cycle is logged around the first hitch. This is `gc=info`, not pause/safepoint profiling: the 0.288-second cycle duration is not a stop-the-world pause. Coarse clock alignment and absent pause details prevent a causal GC claim.

No per-frame GPU timestamps, CPU profiler, or high-resolution command/GC trace was captured. The available evidence cannot identify the cause of either outlier. The main report separately groups eight warmed render views (zero budget misses), this scripted boat scene (two misses), and one scripted chunk traversal scene (zero misses).
