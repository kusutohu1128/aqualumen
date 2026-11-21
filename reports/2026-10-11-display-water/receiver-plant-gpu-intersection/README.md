# Plant GPU intersection — controlled NVIDIA draw/readback, not live adoption

`shaders/lib/water_plant_intersection.glsl` adds the shared GPU triangle/alpha
first-visible-primitive kernel. It is not called by production water reflection
yet. The test compiles this exact file into a fragment program, draws to an
RGBA32F framebuffer and reads the results on the RTX 3080 Ti, rather than checking
only compile/link or repeating the CPU intersection implementation.

The kernel returns status 0 (no hit), 1 (alpha-visible geometric hit) or 2
(unknown). Status 1 is not material/radiance readiness. It computes actual
double-sided triangle intersection, barycentric atlas UVs and triangle normals,
samples the supplied atlas with explicit LOD, and applies the existing terrain
alpha threshold 0.1. Transparent texels continue to later primitives. Unowned
atlas or unqualified alpha produces an unknown barrier at the intersected leaf,
never a ready floor source. Near-coplanar unknown coverage takes precedence within
1e-6 distance regardless of ordering; a materially closer hit still wins.

Primitive packet format: RGBA32F texture of width 4 and height count; each row is
one triangle. First three texels contain position xyz and atlas u. Fourth texel
contains three atlas v values and alpha qualification 0/1. Count is bounded to
1..512, intended as a bounded packet, not a whole-world coverage guarantee.
Invalid extent/count, malformed vertices/UV/qualification, degenerate triangles,
invalid ray/range or unqualified LOD fail closed. Positions must be in the same
camera-relative space as the ray, with all overlapped cells accounted for by the
future producer/index. The maximum validated LOD and ownership flags remain the
producer's responsibility; sampler state and animated atlas freshness also need
the future live ownership contract.

Fresh controlled GPU checks in `../native-plant-intersection-v58.log` prove:

- first opaque leaf stops before the farther opaque fixture;
- transparent hole continues to that fixture;
- actual nearest/linear texture filtering changes coverage as expected;
- explicit mip level changes coverage and excessive LOD rejects;
- missing atlas/alpha ownership blocks farther ready geometry;
- primitive order, coplanar and near-coplanar unknown precedence;
- double-sided and nonaxis-aligned intersections;
- actual diagonal normal output is not forged as an UP cube normal;
- outside/range/nonunit/malformed-UV/extent negatives.

`bash tools/test-receiver-quad-intersection.sh` also remains passing; it is CPU
evidence, not GPU evidence. `git diff --check` reports no whitespace errors.
The GPU atlas and geometry here are controlled synthetic fixtures. Neither this
test nor v57's actual CPU atlas lattice establishes actual-game reflected plant
color, reflection-ray footprint, temporal naturalness, shore quality or speed.
No Minecraft client was launched and normal configs/Mods/saves were not changed
in this checkpoint. The full water/Sun goal remains active and unachieved.

Existing NVIDIA receiver/source controlled regressions also pass via
`build/glcheck shaders --water-world-reflection-only`, retained in
`../native-existing-receiver-after-plant-v58.log`. Their logged production-main/
actual-game source-ownership limitations remain unchanged. The new plant kernel
is exercised separately; this existing command does not test its live integration.

Next: run the GPU kernel against actual owned model/atlas packets; add resource/
frame-qualified upload and conservative spatial membership; unify first-hit
ordering with existing opaque/unknown/interface geometry; shade the selected
actual plant material with its captured lighting. Never treat the entire plant
voxel as empty or borrow an UP floor source for a diagonal leaf.
