# Receiver stage profiling v43 — completed measurement, not accepted

The actual NVIDIA Minecraft client ran the UUID-guarded disposable
AqualumenNaturalV2 world with the v43 candidate and Mod v51. The benchmark
request is `display-water-candidate-20261011-v43`; static and moving samples
are each 20 seconds. The run completed and auto-quit. The native-motion audit
verified 32 PNGs. Java is stopped; `runtime-restored.json` proves exact normal
config/Mods and unchanged ordinary-save hashes, without save rollback.
This is not visual or performance acceptance.

At 1600×800 the static sample measured 0.8395 mean FPS and 1233.186 ms p99;
the moving sample measured 0.8444 mean FPS and 1235.805 ms p99. Each has only
16 measured frame intervals despite the 20-second sample. The longer sample
allowed the unchanged interval-count gate to complete; it did not improve
performance. The experiment is unsuitable for normal use.

Visual inspection of static native `frame-015.png` confirms a visible Sun
inside the sky window, but a distorted/folded perimeter and dark polygonal
exterior remain. This single reviewed frame is not full moving-view acceptance.

Actual receiver stdout at frame 120 reports an 87×36×87 field, 55329 records,
6686 sources, 6715 mesh captures, 54 section copies and 599338 geometry reads.
Inclusive producer wall time is 1112.065392 ms. Its internal stage receipts:

| Stage | Wall milliseconds |
| --- | ---: |
| Collection | 419.756781 |
| Shading and sample composition | 264.400165 |
| Fresh geometry validation | 419.088973 |
| Radiance packing | 3.105580 |
| Meshing (within shading) | 228.992981 |
| Source draw/readback and handling (within shading) | 31.203977 |

These are CPU wall measurements, not independent GPU timings. Nested meshing
and draw values must not be added to the top-level stages. Collection and
validation together account for about 839 ms, so GPU source rendering alone
cannot solve the producer bottleneck. Frame 60 shows the same distribution.

Code inspection also confirms that `Contacts.update()` returns on the same
frame; repeated `ensureUpdate()` calls do not repeat its full contact update.
The per-cell ownership checks still allocate epochs and consult current pack
state, but their individual contribution has not been measured. Do not remove
ownership, fresh validation, unknown geometry or source-attribution guards
based on this receipt. A field-capacity success is not appearance completion.

Next scoped implementation: the geometry adapter now avoids full-cube/solid
reflection queries for cells whose water/fluid/vanilla identity cannot be an
eligible opaque source. Collision and fresh per-cell reads remain unchanged.
CPU classification combinations and run-source tests passed; Mod v52 was
built but not installed. No runtime speedup or visual equivalence is claimed.
