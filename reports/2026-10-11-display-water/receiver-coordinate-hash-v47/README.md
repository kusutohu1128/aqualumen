# Coordinate hash v47 — small observed improvement, not accepted

Actual isolated Minecraft/NVIDIA, 1600×800, UUID-guarded disposable world,
same static/moving scenes and five-second warmup/20-second sample as v44.
Mod v53 changes coordinate hashing only relative to v52; geometry/source
ownership, per-frame capture and fresh validation remain unchanged.

| Scene | v44 mean FPS | v47 mean FPS | v44 p99 ms | v47 p99 ms |
| --- | ---: | ---: | ---: | ---: |
| Static upward | 0.815673 | 0.849654 | 1542.285 | 1462.075 |
| Moving upward | 0.846937 | 0.880839 | 1294.024 | 1217.085 |

There are 17 measured frame intervals in each v47 sample versus 16 in v44.
Mean FPS is about 4% higher in this single paired experiment, not a repeatability
or general-world guarantee. Performance is still unsuitable for normal use.
At frame 60 producer wall time remains 1054.703 ms: collection 406.865 ms,
shading 253.637 ms, fresh validation 384.091 ms, packing 3.322 ms. Its vertical
window differs from v43's warmed receipt; do not infer a controlled stage delta.

Both scenes completed and auto-quit; owned launcher exited zero, Java stopped,
and native-motion audit verified 34 PNGs. Static `frame-016.png` was viewed:
the Sun is visible but sky-window distortion/dark polygonal exterior persist.
This is not full moving-view visual acceptance or completion of the Sun goal.
Normal config/Mods are restored exactly, with unchanged ordinary-save hashes
and no ordinary-save rollback.

Next scoped change addresses the JFR allocation evidence: LoadedReceiverWorld
now binds the same pinned public geometry methods once as typed method handles,
then invokes exact primitive/reference signatures instead of allocating per-call
reflection varargs arrays. Retained chunk lookup, classification, collision,
height qualification and exception-to-unavailable boundaries remain intact.
CPU tests cover primitive constructor/signatures, reference identity, virtual
interface dispatch, signed coordinates, wrong owner, target failure and unexpected
static API. Receiver-field and run-radiance/source controls pass. Mod v54 built
with SHA256 `6c3754e48036e4d7edfa08e35f257796bd39134c164761a203716dc36dfbd1a5`;
it is not installed, and actual Minecraft API compatibility/speedup is unproven.
