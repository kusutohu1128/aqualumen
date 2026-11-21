# Native framebuffer motion, 2026-10-11

The candidate ran in the exact disposable AqualumenNaturalV2 world with NVIDIA,
active Iris and no shader fallback. The experimental benchmark Mod was
`aqualumen-benchmark-0.3.9-native-motion-v2.jar`, SHA256
`eb54a151eeb688d89fb18527b18b0765ed182e30fbfba7beaa8740efe99c15d1`.

`candidate-runtime/native-motion-audit.json` verifies all 91 native PNGs with
the strict PNG integrity reader, sequential indices, finite camera rotations,
actual increasing timestamps, the 10 requests/s bound, and no extra images.
There are 37 underwater rotating frames, 33 near upward frames and 21 dry
rotating frames. The underwater sequence demonstrates more than 30 degrees of
measured yaw change at the requested -65 degree pitch. These checks do not
establish natural appearance or complete continuous-motion visual acceptance.

`candidate-runtime/native-motion-underwater-up-moving/underwater-moving-native.mp4`
is timestamp-driven variable-frame-rate playback, not a claimed 30 FPS recording.
ffprobe reports 1600x800, 37 frames and 4.96 seconds. Native PNG capture overhead
is included in raw frame timings; these are not clean performance measurements.
The sampled intermediate underwater frame still has a broad dark exterior,
strongly warped boundary, and small dark particle-like squares. Their causes
are not proven by appearance alone.

Current source establishes that underwater SSR misses use scatter radiance,
not a sampled seabed. Actual per-pixel hit/miss evidence remains needed before
attributing every dark exterior pixel to this fallback. The optional world
receiver source is not ready in the normal bridge. Do not replace total internal
reflection with invented sky or promote an unqualified receiver experiment.

The launcher exited normally. `runtime-restored.json` verifies exact normal
configs and Mods and unchanged ordinary save bytes, with no save rollback.
This packet has only a candidate run; it is not an optical before/after control.
