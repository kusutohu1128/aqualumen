# Actual terrain draw / Iris vertex-decoder checkpoint

This checkpoint advances per-face refracted-source integration, not visual
acceptance or full-goal completion. Ordinary0.6 / physics0.2 remain unchanged.

## Evidence and bounded result

`actual-draw-readback.json` is from real Minecraft1.21.1 / Iris1.8.8 /
Sodium0.6.9, NVIDIA RTX3080Ti, GL3.2.0 NVIDIA580.173.02. The exact disposable
V2 UUID is `b22dbccb-2970-41e6-847f-f183b1ec923d`; request is
`5ea629da-2a92-4854-bd4f-af647aac1164`. No camera/terrain commands were used.

The original terrain multi-draw snapshot observes program415, VAO134, frame357,
actual28-byte packed attribute layout and bound atlas14 /1024x512. IDs are
context-local. Its listed state survives the owned probe and original call
returns. Effective filters are NEAREST_MIPMAP_LINEAR / NEAREST, REPEAT wrap,
levels0..4, sampler object0. These are metadata, not fragment fetch/LOD evidence.

The owned GPU transform-feedback fixture compiles the **unchanged actually linked
Iris VS**, feeds archived actual14-face /56-vertex initialized words, and reads
448 UV.xy / lightmap.xy / vertexColor.rgba floats. It does not re-run the original
mesher or modify original vertex buffers/program/textures. Padding in the owned
28-byte input is zero; only the eight claimed outputs are qualified, not position,
normal/tangent, projection or fragment lighting. Listed GL state is restored;
this is not an exhaustive all-GL-state proof or the original fragment invocation.

Observed light matrix has diagonal1/256 and translation1/32. Iris passes raw
encoded light bytes directly into it, unlike generic Sodium's /256 convention.
Observed UV shrink is `[2.6702880859375e-5, 2.288818359375e-5]`. The new public
CPU decoder and independent scalar audit both match all448 saved GPU floats
with maximum float32 error0. Actual decoded lightmap range is0.0625..0.78125.
No guessed AO1 or neighbor block-light replacement is used.

Three public API increments establish real-output decoding, nonfinite matrix
rejection and unsupported encoded light rejection. Initial RED is an unimplemented
CPU API, **not a shader defect**. Independent reader RED is likewise an
unimplemented reader. Six copied external-negative controls reject double light
conversion, altered AO, wrong stride, altered VS source, state-restoration failure,
and original-fragment overclaim. Final checks include uniform snapshot immutability.

The initial observer compile failed on a wrong LWJGL constant. The failed sources
and compile log remain under `actual-build`; successful corrected build is under
`actual-build-v2`, selected by `build-receipt.json`. It is not a GPU/GLSL RED.
Observer JAR SHA256 is
`0561fb92271443455b2c86cfb53574d55886d2e67561ca8d93dc6e01771d3c46`.

## Preservation and unfinished work

Clean owned TEST handle49872 exits0, then no Java is present. The probe JAR and
opt-in are recoverably moved to baseline cache's `disabled-probe`. Ordinary41
saved files, three configs and three Mod hashes match the fresh post-save
baseline before reopening. **No ordinary save rollback.** `checkpoint.json`
records the fresh normal-account owned handle, lock, activation, subsequent
root-inspected gameplay/pause and all12 absent TEST entry points. Launcher
authentication logs stay private, outside this report.

On normal startup Iris re-saves its properties: only the timestamp comment changes
from17:11:09 to17:31:30 JST. All property lines are byte-identical; options and
benchmark config remain byte-identical. Both Iris files and their hashes are
retained. The byte-exact three-config claim applies **before normal reopening**,
not to the naturally regenerated timestamp at runtime. No live config overwrite.

No production GLSL changed; retained native qualification is hash-checked, not
unnecessarily re-run. No standalone/native GL runs after normal reopen. New
Minecraft frame timings are not measured. The TEST image remains strongly cyan
with serrated shore bands. This checkpoint does not fix that appearance.

Pending: actual triangle interpolation and material filtered fetch, shared
terrain illumination/paired Sun radiance, coherent geometry/resource epochs,
safe dynamic Iris source binding, partial-water/displaced interfaces and actual
natural-view/motion/weather/contact validation. See RESUME.md. Full goal active.
