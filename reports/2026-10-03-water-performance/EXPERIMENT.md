# Water render performance attribution

This experiment changes observation only, not the optical algorithm, source
weights, support certificate, inverse, fallback or permission policy. Existing
`2026-10-03-water-sun-support` evidence remains frozen.

Question: how much of the measured whole-client frame interval is spent in the
fresh render-thread Sun authorization (including the complete selected ZIP
read/hash), rather than GPU work or other client work?

Use the frozen zero-physical ZIP SHA-256
`33164466c3828daa93724d6b9e531fcb66897e300ecd16dc4cfa90ec08c38cda`
in the exact disposable AqualumenNaturalV2 world,
UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`, seed308060.
No ordinary-world camera/time/terrain automation or save restoration.

Matched controls: 1600x900, render12/simulation6, cap120, VSync off,
underwater-up-near/deep/tilt, fixed shader phase120 and tessellation factor4,
10-second warmup and >=5-second sample. All observer request files absent
during measurement. Pin active pack/JARs, actual options, JVM/GC and actual
camera. Observe GPU clocks, utilization, temperature and power; those are
context, not isolated GPU stage timings.

Before runtime, add a TEST-only aggregate profiler and CPU tests. Preserve every
fresh filesystem, world, pipeline, physics and complete ZIP read/hash check,
ordering, exceptions and fail-closed result. No authorization/digest cache.
Export after sampling, not per call. Record call counts, permission outcomes,
total authorization duration and nested read/hash duration, grouped by Iris
frame and supplier identity. Distinguish uniform work from observer/Recorder
setup/finish checks. Include a matched timer/counter-overhead control; do not
claim the instrumented timings are zero-overhead or Minecraft GPU timings.

Only root operates the live game/GPU. Cleanly save/quit the owned normal client
before any TEST launch; restore normal0.6/physics0.2, original settings and
disabled TEST opt-ins at handoff. Preserve unsuccessful evidence separately.

Success for this slice is measured attribution with unchanged safety/optics,
not visual or full-goal acceptance. The dark rim/bands and motion remain open.
