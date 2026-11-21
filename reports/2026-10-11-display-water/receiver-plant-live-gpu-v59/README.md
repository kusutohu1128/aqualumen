# Plant live GPU v59 — actual model/atlas draw, not reflection integration

`ReceiverPlantPacket` serializes owned decoded model quads into immutable,
epoch-tagged GPU triangle packets. World positions are made relative to an
explicit reference point, bounded to ±128; UVs remain decoded atlas coordinates.
Packets reject foreign world/frame/resource epochs and are bounded to 256 quads/
512 triangles. Each triangle retains its alpha qualification separately from
any material/radiance readiness.

`ReceiverPlantGpuProbe` uploads packets and ray arrays, samples the actual owned
terrain atlas/sampler with the shared GLSL intersection kernel, and reads back an
RGBA32F output. It restores program, VAO, separate framebuffer bindings, viewport,
polygon modes, indexed blends/color masks, enable flags, pixel-pack state/PBO,
active texture and texture/sampler bindings. Cleanup uses a context/thread guard
independent of frame expiry. The kernel is embedded in the Mod; embedded and
working GLSL SHA256 both equal
`b265807dc20ac307bdb361c3b63cc7b80f7de777216bf81224e88a51a6c28de6`.

Fresh controlled NVIDIA tests in `../native-plant-packet-v59.log` exercise actual
packet upload/draw/readback plus hostile rasterizer/scissor/polygon/blend/color-
mask and pack/PBO states. Success and shader-compile-failure restoration pass.
An initial test setup incorrectly used separate polygon modes on a core context;
the test now follows the actual core/compatibility profile. This was a test setup
error, not an accepted GPU probe failure. Existing shared-kernel intersection
cases remain passing. Packet-copy and world/frame/resource identity negatives
are CPU checks, not live unload/reload evidence.

Actual disposable Lab initial-terrain frame 3/resources 1:

- tall_seagrass at 449,47,-392: 16 actual model triangles, 240 constructed rays;
  GPU results 152 clear, 88 alpha-visible, 0 unknown;
- seagrass at 449,47,-390: 16 actual model triangles, 240 constructed rays;
  GPU results 160 clear, 80 alpha-visible, 0 unknown;
- actual 1024×512 atlas and captured sampler; point footprint, explicit LOD 0;
- following normal source publication remains ready=2 with 6748 sources,
  55983 records and unknownKinds=false; field is not reclassified.

Rays are diagnostic triangle-lattice points offset 0.2 along each actual triangle
normal, aimed back through that model with range 1. They are not camera reflection
rays, unique scene samples or area-weighted transparency. The packet contains one
plant model, not surrounding banks/floor/neighbor plants. Status 1 only means
alpha-visible geometric hit and never means shaded source readiness. Kelp variants
were not encountered. Actual GPU ownership-negative/reload controls, reflected
ray footprint/LOD and material radiance remain unverified in Minecraft.

Artifacts:

- Mod `build/aqualumen-physics-0.3.0-plant-live-gpu-v68.jar`, SHA256
  `18537b00fb3f264d2b9e67684f18b04f7c80db008f8678aa3b6e55cd0fb978ab`;
- pack `dist/Aqualumen-DisplayWater-PlantLiveGPU-v59-2026-10-11.zip`;
- shader compile-only `../native-plant-live-gpu-compile-v59.log`;
- CPU/GL alpha controls `../native-atlas-after-plant-live-v59.log`.

The actual run `display-water-candidate-20261011-v59` completed static/moving
underwater phases and the owned launcher exited 0. Collector verified exact
pack identity, NVIDIA renderer and active Iris/no fallback. `candidate-runtime`
and `candidate-receiver-runtime.log` retain evidence. The native audit verified
61 PNG files; images were not visually reviewed for acceptance.
`runtime-restored.json` proves exact normal configs/Mods and unchanged ordinary
saves, with no save rollback or launcher change to instance config.

Next required integration is conservative all-overlapped-cell model indexing,
joint first-hit ordering with existing opaque/unknown/interface geometry,
resource/frame-owned publication to water shaders, and shading the actual chosen
leaf using its own material/light. This diagnostic does not repair the ordinary
water reflection or complete the Sun/underwater-sky goal.
