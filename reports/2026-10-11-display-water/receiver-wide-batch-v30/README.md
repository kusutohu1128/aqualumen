# Rejected wide-source runtime attempt

V42 expanded the candidate field to 33x36x33 and reused private section/mesh
contexts with a batched source draw. Actual Minecraft terminated before the
benchmark started: the existing raw texture uploader still limited width to 64,
while the new source batch exceeded that width. `receiver-failure.log` records
the exact exception and `runtime-failure.json` identifies the stopped attempt.
No rendered improvement, successful publication or timing acceptance is claimed.

Java absence was verified. The server log recorded world saves and worker
shutdown. The owned Prism process had no child game process and was explicitly
terminated afterward (launcher exit 143, not a normal Minecraft exit).
`runtime-restored.json` verifies exact normal configs/Mods/instance settings and
ordinary save hashes, without save rollback. This rejected packet was preserved.

The subsequent V43 fixes the raw uploader's width contract, retaining its 65536
texel bound, adds 65/4096-wide native upload/readback/state-restoration tests,
and prevents optional producer RuntimeExceptions from terminating Minecraft.
Recovery into the new v31 packet requires an explicit stopped-packet flag and
revalidates the exact prior log hash, terminal launcher, restored normal configs,
Mods, instance settings and ordinary saves. Unknown crashes are not clean exits
and are not admitted by this recovery path.
