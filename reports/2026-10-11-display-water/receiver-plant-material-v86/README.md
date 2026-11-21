# Actual plant region material diagnostic v86

Run: `display-water-candidate-20261011-v86`, request
`b01ed09d-6ce3-417a-a32b-aaa56bb70df4`, disposable world UUID
`b22dbccb-2970-41e6-847f-f183b1ec923d` in Aqualumen Lab.

Pack: `Aqualumen-DisplayWater-PlantMaterial-v86-2026-10-11.zip`.
Mod: `aqualumen-physics-0.3.0-material-region-gpu-v96.jar`, SHA256
`7539300e05e961a6befe51984cd5ae5afd77bde3af9ae401423681ffd62e05a0`.
The pack contains the current source including explicit cutout alpha mode;
ordinary plant tracing/shading macros remain disabled.

Actual Minecraft diagnostic at frame 3/resources 1 confirms 74 models,
1,184 triangles, 28,416 material attributes and exact RGBA32F upload/readback.
Region index has 10,608 memberships, no unavailable sampled models or unloaded
sampled cells. Owner states were validated, but complete model-owner coverage
remains false and trace admission remains false. This is not live leaf-reflection
acceptance or proof that external owner spill cannot affect the sampled cells.

Two 1600x800 scenarios used 5-second warmup and 20-second samples without JFR:

- Underwater-up-near: 42 frames, mean 2.111827243601461 FPS.
- Underwater-up-moving: 43 frames, mean 2.1883685858843465 FPS.

The native motion file audit verified 85 PNGs, not temporal naturalness. The
near principal PNG was visually inspected: pronounced compressed/folded sky
window edges and dark polygonal exterior remain. No visual correction or usable
performance is claimed; the moving sequence was not visually reviewed.

The owned launcher exited with code 0. Collection completed and the helper
verified exact restoration of normal configuration/Mods, without save rollback.
No Java process remained. The ordinary save was not operated on. No candidate
was adopted into ordinary play.
