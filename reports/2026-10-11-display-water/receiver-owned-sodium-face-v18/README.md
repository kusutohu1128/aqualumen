# Actual owned Sodium face intake

The corrected adapter obtained one qualified full-unit top face from an owned
Sodium BlockRenderCache/ChunkBuildBuffers invocation at frame 2/resource generation
1 for gravel (448,45,-384). `source-runtime.log` retains all four actual
pre-encoder positions, atlas UVs, color, AO and packed light. AO is 0.5999756 on
two corners and 1.0 on the others; packed light is 0 and color is white. Those
values are copied, not replaced by default AO/skylight or shaded radiance.

The actual normalFace POS_Y is now mapped to canonical UP. The scope matches the
same world, renderer, cell and state, validates one complete unit face and owns
immutable input copies. Dedicated render/cache/native mesh buffers are released;
no actual terrain mesh is submitted or shared worker buffer read. Only already
loaded 3x3 neighbor columns are admitted before cloned-context preparation.

Seagrass above this material remains unsupported by water-ray traversal. This
material-only scan does not establish a camera-hidden first receiver or allow
searching a ray through vegetation to a farther floor. Source input size stays
zero and no natural reflected radiance is published.

Evidence: `../receiver-owned-sodium-face-map-test.log` verifies scoped ownership,
copies, naming and rejection controls in CPU fixtures; `../receiver-owned-sodium-face-map-build.log`
records complete Mod compilation. Actual NVIDIA/Iris near view completed without
fallback; native sequence audit verified 32 PNGs. This is not actual filtered
atlas sampling, shader-decoded/interpolated attributes for this new capture,
C10/C11 radiance, whole-volume production, reload or visual/FPS acceptance.

Experimental Mod SHA256:
`c6c036ee026666338be17b96a4911078ba2206699daf7e1df93a63ff796ac226`.
The client exited normally; `runtime-restored.json` verifies exact normal config,
mods and ordinary-save bytes without rolling back any save. The full goal is open.
