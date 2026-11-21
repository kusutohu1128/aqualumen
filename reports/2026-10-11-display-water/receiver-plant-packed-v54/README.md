# Plant packed v54 — owned model UV qualification

Raw Sodium UVs alone do not establish the UVs used by the actual terrain shader.
The pinned Iris encoder quantizes UVs and its vertex shader applies the captured
u_TexCoordShrink uniform. Plant model capture now owns the encoder output for
every model quad and decodes it with the actual terrain uniforms rather than
sampling raw UVs as if they were shader-equivalent.

Changes:

- geometry faces retain prepared separate-AO color/light, actual packed UV/
  color/light codes and stride, with defensive copies;
- every accepted model quad must receive exactly one valid encoder output;
- missing, skipped, malformed or duplicate encoding fails the whole model;
- color/light mismatch rejection applies to each plant quad, not only cube UP;
- geometry snapshots cannot admit faces without their four encoded vertices;
- terrain decode verifies epoch and converts captured positions using actual
  block owner and renderer offsets, without clipping to the owner voxel;
- alpha remains UNKNOWN: no texture transparency or plant radiance is invented.

Actual initial-terrain receipts in UUID-guarded Aqualumen Lab, frame 3/resources 1:

- tall_seagrass at 449,47,-392: 8 captured/decoded quads, all non-UP;
- seagrass at 449,47,-390: 8 captured/decoded quads, all non-UP;
- both report rawUV=true, packedUV=true, alphaReady=false, radianceReady=false;
- field remains unchanged; kelp variants were not encountered in this probe.

This proves actual model encoding and bounded UV decoding for these two models,
not atlas-alpha correctness, first-hit GPU attribution, lighting or visual repair.
Only the exact v54 diagnostic pack executes the one-shot probe. Normal packs do
not execute it. Existing opaque top-face source qualification remains separate.

Validation: expanded CPU scope tests cover defensive packed copies, incomplete/
skipped/duplicate encodings and existing ownership/geometry negatives; existing
quad-intersection tests remain passing. The 15 Python runtime/diagnostic tests
pass. Full Mod build and NVIDIA shader compile/link pass, not draw/readback.

Artifacts:

- `build/aqualumen-physics-0.3.0-plant-packed-probe-v62.jar`;
- Mod SHA256: `123223c0c2beff6d2f96951c96bb2d04ff4c1c585219a02b8a06a3fd9b6a0250`;
- `dist/Aqualumen-DisplayWater-PlantPackedProbe-v54-2026-10-11.zip`;
- `../native-plant-packed-compile-v54.log`.

The actual run `display-water-candidate-20261011-v54` completed static and moving
underwater phases, with the owned launcher exiting 0. The collector verified
NVIDIA renderer, exact pack identity and active Iris/no fallback and retained
`candidate-runtime` plus `candidate-receiver-runtime.log`. The motion audit
verified 58 native PNG files; images were not visually reviewed for acceptance.
`runtime-restored.json` proves byte-exact normal config/Mods and unchanged ordinary
saves, without save rollback or instance-config change by the launcher.

`bash tools/test-receiver-vertex-shader.sh` also verified the current decoder
against 448 retained GPU UV/lightmap/color floats from the archived 2026-10-06
fixture (maximum difference 0). This is CPU comparison against historical real
GPU observations, not a fresh GPU decode/readback of v54 plant vertices.

Next required work is sampler/resource-owned actual atlas alpha and material
shading, conservative spatial coverage of model offsets, and GPU first-hit tests
before plant cells may replace the current whole-voxel unknown barrier.
