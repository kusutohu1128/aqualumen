# Lazy solid qualification v44 — measured, not accepted

Actual Minecraft/NVIDIA, 1600×800, the UUID-guarded AqualumenNaturalV2 world,
same static/moving scenes, five-second warmup and 20-second sample as v43.
Candidate uses Mod v52 (`4a3a3b9ae4dc404738f84b57db3272799b2eab6493a5075ded09746c3b80c3df`).
The sole producer change avoids full-cube/solid queries for water, air and
non-eligible identities; collision and current geometry reads remain intact.

| Scene | v43 mean FPS | v44 mean FPS | v43 p99 ms | v44 p99 ms |
| --- | ---: | ---: | ---: | ---: |
| Static upward | 0.839504 | 0.815673 | 1233.186 | 1542.285 |
| Moving upward | 0.844434 | 0.846937 | 1235.805 | 1294.024 |

Both samples contain 16 measured frame intervals. This single paired run does
not establish a speedup; static mean and both p99 values are worse. Do not
present the CPU-query reduction as a performance fix or adopt the experiment.
The startup producer receipt uses a different vertical window than the warmed
v43 receipt, so those stage durations are not a controlled comparison.

Both scenarios completed, the owned launcher exited zero, and the native-motion
audit verified 32 PNGs. Actual static `frame-015.png` was viewed: Sun visible,
but a distorted sky-window perimeter and dark polygonal exterior persist.
Wave phase differs from v43; this is not pixelwise visual equivalence or full
moving-view acceptance. The full appearance objective remains unachieved.

CPU receiver-field classification combinations, independent slab controls,
run-radiance/source composition tests and nine runtime safety tests passed.
Mod v52 built and was used in this runtime. Java is stopped; restoration proves
exact normal config/Mods and unchanged ordinary-save hashes, without rollback.

Next: sample actual producer stacks rather than removing safety checks or
optimizing another presumed hotspot. The pinned runtime has `jcmd` and `jfr`,
so a disposable-world-only JFR can distinguish geometry reflection, cache
allocation/lookup, ownership checks and source meshing. A recording must be
explicitly tied to the owned Java process and must not expose launcher secrets.
