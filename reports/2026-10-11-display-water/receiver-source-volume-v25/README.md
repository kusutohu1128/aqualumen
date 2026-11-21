# First bounded live source publication

At frame 3/resource generation 1, the owned intake and unchanged actual GPU
shared-source fragment produced one qualified exposed top source in a 3x36x3
field at (447,32,-385). Four paired geometry/total/Sun/face RGBA32F textures were
transactionally published with ready 2. `source-runtime.log` retains the receipt.

Only pure water below another pure water block is marked full-water. Partial
surface cells, seagrass, other unsupported geometry and unloaded cells remain
unknown; opaque first geometry is retained even without source. Full-water
exposure is required before shading a top face, and geometry is rechecked after
all shading. Supplied source epoch and block identity must match the capture.
No ray is allowed to bypass vegetation to find a farther floor.

This first attempt proved producer/upload, but did not obtain the corresponding
positive water-draw binding receipt. It is a one-shot frame-3 publication, not a
per-frame producer; later epochs are unavailable. The face-center point is a
piecewise-constant voxel approximation, not a reflection footprint or voxel
mean. It is not a visual fix or natural reflection-hit acceptance.

`../receiver-source-volume-test.log` covers layout, paired supplied RGB,
unready/stale/identity/geometry-change/unloaded controls in CPU fixtures. The
actual NVIDIA/Iris near run completed without fallback, with 32 validated PNGs.
Normal config/Mods, instance settings and ordinary-save hashes were restored
exactly, without save rollback. Experimental Mod SHA256:
`055265de746322003d98ae1ada06a66ea9cb8d1697a8185440fedef27bd264a2`.
