# Plant alpha v57 — actual base-level atlas/UV evidence

The readback now explicitly supports unsized GL_RGBA, matching the actual
Minecraft atlas storage identified by v56. It still rejects alpha-less RGB,
unsupported storage, nonzero base level, nonordinary alpha swizzle and texture
comparison. Readback preserves texture binding, pixel-pack layout and PBO.
Immutable CPU base-level sampling supports nearest/linear and repeat/clamp.
This is diagnostic data acquisition, not implicit-LOD terrain sampling parity.

Actual Lab initial-terrain frame 3/resources 1:

- owned atlas 1024×512, minFilter=9986 (NEAREST_MIPMAP_LINEAR), magFilter=9728
  (NEAREST), wrap S/T=10497 (REPEAT);
- tall_seagrass at 449,47,-392: 8 decoded model quads, 1072 transparent and 1376
  opaque base-level triangle-lattice samples;
- seagrass at 449,47,-390: 8 decoded model quads, 1744 transparent and 704 opaque
  base-level triangle-lattice samples;
- both keep alphaReady=false and radianceReady=false; field remains unchanged.

The 2448 samples per model are deterministic barycentric UV lattice points over
both triangles of all eight quads (including duplicated/reversed faces and
edges). They are not area-weighted coverage, unique texels, reflected pixels or
counts of rays. The split uses the production terrain alpha discard threshold
0.1 on actual atlas bytes with captured base-level filtering/wrap metadata.
Kelp variants were not encountered in this initial one-shot probe.

Controlled tests:

- CPU immutable alpha/orientation/filtering/wrap tests;
- fresh NVIDIA GL RGBA, RGBA8 and SRGB8_ALPHA8 byte readback;
- actual requested unsized RGBA remains observed format 6408;
- hostile pixel-pack/PBO and unsupported-base-level restoration;
- expanded alpha-less RGB rejection and failure restoration;
- existing scope/intersection tests and 15 runtime/diagnostic Python tests pass.

`../native-atlas-alpha-v57.log` retains initial GPU checks;
`../native-atlas-alpha-expanded-v57.log` retains RGB-negative checks.
`../native-plant-alpha-rgba-compile-v57.log` is compile/link only, not draw or
readback. The Mod is `build/aqualumen-physics-0.3.0-plant-alpha-rgba-v66.jar`, SHA256
`d6cb5de6bc18f520d8ac374bfb70d6b2f1202e8919ea393dd41dc6e595087b8c`.
The pack is `dist/Aqualumen-DisplayWater-PlantAlphaRGBA-v57-2026-10-11.zip`.

The actual run `display-water-candidate-20261011-v57` completed static/moving
underwater phases and owned launcher exit 0. Collector verified NVIDIA renderer,
exact pack identity and active Iris/no fallback. `candidate-runtime` and
`candidate-receiver-runtime.log` retain artifacts/receipts. Native audit verified
59 PNG files, not visual quality; images were not visually reviewed for acceptance.
`runtime-restored.json` proves exact normal configs/Mods and unchanged ordinary
saves, without save rollback or launcher change to instance config.

Next required integration is explicit reflection-ray texture footprint/LOD,
GPU first-visible-primitive attribution and matching plant material lighting.
CPU base-level lattice sampling must not by itself reclassify plant voxels or
claim renderer parity/visual repair. Animated texture freshness is only this
captured frame, not a persistent resource-lifetime guarantee.
