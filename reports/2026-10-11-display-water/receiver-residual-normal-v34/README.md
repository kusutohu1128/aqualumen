# Rejected raster-plus-residual normal candidate

This checkpoint does not satisfy the full Sun/underwater appearance goal.

The candidate added detail-1 minus detail-0 spectral slopes to the actual raster
facet and omitted a second underwater ripple perturbation. NVIDIA full shader
checks and supplied backface fixtures passed, but they did not predict natural
interface appearance.

Actual Aqualumen Lab / UUID-guarded AqualumenNaturalV2 captured 47 native PNGs.
Moving frame-015 was actually viewed: obvious triangle-shaped seams are visible
across the sky window, and the folded rim and dark exterior remain. The source
optical-normal change was reverted. The rejected pack and receipts remain for
diagnosis; no appearance improvement or full-motion acceptance is claimed.

At 1600x800 with native capture, static: 27 frames, mean 5.557524 FPS, p99
297.704321ms; moving: 28 frames, mean 5.736470 FPS, p99 193.672515ms. These
separate samples do not establish a controlled speed improvement.

Launcher exited normally (0). Normal configs, Mods, instance settings and
ordinary save hashes were restored exactly without save rollback.
`candidate-receiver-runtime.log` contains only receiver-tagged stdout lines;
unrelated/private launcher log content is not archived. The filtering has a CPU
unit test. Actual reflected receiver-hit acceptance remains unproven.

The next normal treatment must address continuity and unresolved slope
distribution near the critical angle, rather than simply substituting a flat
triangle slope or discarding high-frequency waves.
