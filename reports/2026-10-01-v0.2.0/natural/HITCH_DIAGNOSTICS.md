# Scripted boat-contact hitch observations

This supplements the accepted `natural-v2-final-zgc` measurements; it does not change or discard raw samples. The boat scene contains 9,736 measured intervals over 30 seconds, with two intervals exceeding 16.667 ms.

| CSV frame (zero-based) | Interval ms | Cumulative interval end, seconds after sampling boundary |
|---|---:|---:|
| 3858 | 70.055848 | 11.777760 |
| 5229 | 35.184969 | 16.008997 |

Cumulative times are reconstructed from raw CSV nanoseconds; the recorder discards the first start boundary. The game log places the sampling boundary at 21:51:01 JST, with only whole-second precision.

The bridge was active and reported one contact in all 31 once-per-second/end-of-sample snapshots; 30 reported nonzero force, with a maximum of 8.0. The reset counter stayed at 5 throughout. These snapshots establish that real contact inputs were present, but are too sparse to attribute a particular slow frame to the physics bridge or GPU solver.

`logs/latest.log` contains 3,203 vanilla boat `moved wrongly` warnings between 21:51:01 and 21:51:31 JST (60–206 per whole-second bin). The benchmark translates the mounted boat using server teleport commands at 6 m/s, nominally 20 Hz. This is therefore a scripted contact/correction workload, not normal player-controlled rowing. Repeated warnings are directly observed; their share of the frame delay is not measured.

The matching process started at 21:41:06 JST according to `ps`. `logs/aqualumen-gc.log` records a concurrent ZGC minor collection at JVM uptime 612.079–612.366 seconds, approximately around the second hitch, and no contemporaneous logged collection around the first hitch. The log is `gc=info`, not pause/safepoint profiling: the 0.288-second collection duration is not a stop-the-world pause. Clock alignment is only approximate, so this is correlation, not proof of a GC cause.

No per-frame GPU timestamps, CPU profiler or high-resolution command/GC event trace was captured. The available evidence cannot identify either hitch's cause. Both misses remain in the reported result; this run does not demonstrate an absolute 60 FPS floor for the scripted boat workload.
