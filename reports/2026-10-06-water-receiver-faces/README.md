# Actual pinned Minecraft receiver face inputs — partial progress

The intended next step from the sealed original-MAIN two-RED regression was
implemented and runtime-tested: actual vanilla full-face model/atlas/UV/tint/raw
lighting inputs, without guessing material colors or using a camera-pixel proxy.
This does **not** fix or promote the production water renderer. Full realism goal
remains active; cyan/serrated water bands remain visible in the actual TEST view.

## Actual runtime result

- Exact isolated Lab / AqualumenNaturalV2 UUID
  `b22dbccb-2970-41e6-847f-f183b1ec923d`, actual integrated seed308060.
- Real Minecraft1.21.1 / Iris1.8.8 / Sodium0.6.9, NVIDIA RTX3080Ti,
  GL3.2.0 NVIDIA580.173.02, original normal0.6 shader and physics0.2.
- Standalone TEST-only face probe0.1.0-v1, SHA256
  `9731f933b1f72cfaac94d44f0f401aaa063cd549035897feb11e9984b20739e6`.
  A new exclusive deterministic rebuild matches the actually installed JAR bytes.
- One request `e40c1d67-ddcf-493e-8b4e-af03f7e6f585`, actual frame1:
  all16 original saved first-sand face requests captured (14 unique cell-faces).
  Includes14 UP records, one WEST, one EAST; the previously audited eight hidden
  and eight visible receivers. Duplicate records are intentionally not removed.
- Atlas `minecraft:textures/atlas/blocks.png`, sprite `minecraft:block/sand`.
  Actual rendering seeds select different affine UV orientations. Unshaded
  vertex color/tint are white; raw adjacent sky light8..12, block light0.
  Every actual render-view brightness is1.0 in this Iris/Sodium context.
- The separate CPU audit joins requested position/normal identities to the
  old saved first-hit scope and validates UV corners and point-in-face mapping,
  raw-light/color ranges and request/hash/UUID scope. It does not reproduce
  Minecraft model selection independently or assert fragment-simultaneous state.

The adapter and decoder are optional root candidates, **not** enabled by the
normal installed physics0.2 Mod. The TEST Mixin only registers a readback listener;
no uniforms, texture allocation/upload, GL access, Minecraft commands or world
mutations are introduced. Loaded-only geometry and tint neighborhood guards
prevent missing chunk generation. Unsupported/partial/non-affine/extra-face
models and nonuniform/transparent vertex colors stay unready.

## Qualification limits

This is actual vanilla-facing API input evidence under Iris/Sodium, not shaded
material radiance, texture pixel colors, AO or smoothed per-vertex lighting.
Frame1 readback does not qualify lighting warmth, temporal stability or shared
snapshot/atlas lifetime. Neither the source-volume sampler nor the original
water MAIN has been connected. The earlier hidden-source-zero and wrong-farther-
source-color REDs remain unresolved. No new Minecraft timing benchmark, C0
passivity measurement or visual quality acceptance was run.

`test-runtime.png` and pause/exit images are separate later screenshots, not
the exact face-readback frame. The TEST image still shows the known water bands.
No completed phase0/45, geometry role pair, saved-ray replay or9->32 budget
experiment was rerun. Focused decoder/geometry/bathymetry CPU checks were rerun
as affected adapter regressions, not substituted for real rendering acceptance.

## Recovery / ordinary handoff

Old ordinary owned41749 genuinely exits0 after All dimensions saved and title
Quit. A fresh normal41-file baseline is captured before adding the probe.
TEST owned28525 genuinely exits0 after clean save and menu Quit. The probe JAR
and enable properties are moved recoverably to the private backup's
`disabled-probe/`; original configs/three Mods/41 ordinary saved files match
exactly before normal reopening. No save restoration or ordinary-world commands.

Authentication launcher logs stay private under
`/home/kusutohu/.cache/aqualumen-legacy-branch-host-receiver-faces-oo78k4in`.
Only nonsecret game logs and request/evidence enter this packet. UI actions sent
while the TEST saving screen was still active did not establish Quit focus;
actual title images were re-inspected and Return on focused Quit produced exit0.
No window destruction, process kill or timeout-based relaunch was used.

The final checkpoint and normal screenshots prove fresh ordinary0.6/physics0.2
reopening and pause, with all TEST controls absent. No native GL after normal
relaunch. See [next action](RESUME.md); the report is not goal completion.
