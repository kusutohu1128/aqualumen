# Actual-input full-face triangle interpolation

This checkpoint implements the per-face attribute sampler needed by real refracted
source shading. It does not accept natural water appearance or complete the goal.

## Qualified result

The installed Sodium0.6.9 public CPU index generator runs unmodified for14 quads
in both SHORT and INTEGER formats. Both produce local indices `[0,1,2,2,3,0]`.
Pinned DefaultChunkRenderer bytecode establishes the opaque shared-index buffer,
TRIANGLES mode and UNSIGNED_INT draw path. The BlockRenderer/archived mesher
preserve vertex order; no corner sorting or guessed AO diagonal is introduced.
This is implementation-boundary qualification, **not a live original index-buffer
read** or proof of original14 GPU draw ownership.

`ReceiverTriangle` owns supported full-unit face data, samples each containing
triangle, preserves decoded UV/lightmap/ABGR channels and supplies local analytic
gradients. Three public RED->GREENs establish sampling, unqualified-diagonal
rejection and degenerate-face rejection. These REDs are previously unimplemented
CPU behaviors, not shader faults. Caller reuse, missing/nonfinite/outside controls
and supplemental varying affine UV gradient checks pass. Local gradients do not
prove actual projected derivatives, material LOD or filtered atlas fetch.

The standalone native fixture runs the unchanged actually linked Iris VS archived
in the prior draw packet (SHA256
`34385676ea69a47b1ccec5e200f75e7faeed6c15cd274e5dc36c926754d1bb3a`).
It uploads the initialized first20 bytes of56 actual encoded vertices into owned
28-byte-stride inputs; remaining padding is zero. Only UV/lightmap/color outputs
are qualified, not encoded normal/tangent, material shading or actual projection.
The fragment shader is a disclosed pass-through observer, **not terrainLight**.
Original vanilla/Iris files, production shaders and installed assets are unchanged.

NVIDIA RTX3080Ti GL4.6.0 / driver580.173.02 renders16 saved first-receiver points
and42 supplemental interior points under orthographic and projective transforms:
116 positive samples /928 floats. Independent reader maximum error is
`8.731773242232066e-7`, below the declared viewport/subpixel/float32 bound
`1.45885009765625e-5`. All928 deliberate opposite-diagonal output floats are also
qualified against their own independent expected values, while their maximum
difference from the correct diagonal is `0.10196083784103394`. This is a sensitive
negative control, not an artifact to desaturate or average away.

Saved raw outputs contain1856 floats. The public independent reader rejects copied
AO substitution, positive/negative relabeling, owner detachment and changed source.
The native compiler succeeds with three misleading-indentation warnings; its actual
log and executed sources are retained, not called warning-free. No production
shader changed, so completed native shader regressions are retained/hash-checked,
not replayed without a reason. The actual previous Minecraft context is GL3.2;
the new standalone context is GL4.6. These are not Minecraft frame measurements.

## Ordinary runtime preservation

Previous owned ordinary handle1355 / Java3470645 is saved through inspected
Save/Quit and title Quit, exits0, then no Java is present. A fresh post-save
41-file/config/three-Mod baseline is taken, not an old save rollback. The native
fixture leaves that snapshot exact. No TEST world/client, probe JAR, opt-in,
shaderpack, normal Mod or config is installed/edited this cycle. Normal0.6 /
physics0.2 is reopened, freshly inspected in gameplay and subsequent pause,
with ownership and12 absent opt-ins recorded in checkpoint. No native GL after
normal reopening. Iris's normal startup timestamp-only comment change is retained
separately; actual settings stay identical. Auth launcher logs remain private.

## Unfinished full goal

The strong cyan/serrated shoreline remains unaccepted; no new natural visual or
motion claim is made. Still required: actual material filtered fetch/footprint,
original shared illumination and paired direct Sun, coherent live geometry /
atlas/light epochs, safe dynamic Iris source binding, full water/displaced-interface
membership, actual natural view/motion/weather/contact checks and honest timings.
See RESUME.md. Full realistic water/light/physics goal active, not achieved.
