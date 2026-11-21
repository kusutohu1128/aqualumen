# Plant model v53 — actual Sodium capture evidence, not reflection acceptance

The exact v53 pack gates a once-per-process bounded read-only model probe. Normal
packs do not execute it. The probe scans loaded cells in a 17×15×17 maximum
camera-adjacent region, captures at most one model per each of four supported
plant IDs, and leaves receiver geometry, eligibility and radiance unchanged.
Unavailable captures remain unavailable, with no empty-water substitution.

Actual Aqualumen Lab disposable-world receipts on 2026-10-11:

- frame 3/resources 1, tall_seagrass at 449,47,-392: 8 quads, all 8 non-UP;
- frame 3/resources 1, seagrass at 449,47,-390: 8 quads, all 8 non-UP;
- both copied raw atlas UVs and actual local X extents 0..1;
- probe finished with 2 encountered plant kinds, field unchanged;
- alphaReady=false and radianceReady=false explicitly retained.

These receipts prove the actual Sodium renderModel path reaches the new all-face
capture mode for these two models. They do not prove kelp/kelp_plant capture (none
encountered in this one-shot region), global model-offset bounds, atlas-alpha
sampling, GPU first-hit ordering, plant lighting, visual improvement or speed.
The probe runs at initial terrain capture, not once per benchmark scene.

Artifacts:

- pack: `dist/Aqualumen-DisplayWater-PlantModelProbe-v53-2026-10-11.zip`;
- Mod: `build/aqualumen-physics-0.3.0-plant-model-probe-v61.jar`;
- Mod SHA256: `2c65638171e055d7ccd4810c457dec4f5c4b09553de0988c509445e0b4c194b8`;
- native compile-only log: `../native-plant-model-compile-v53.log`;
- raw scoped model receipts: `candidate-receiver-runtime.log`.

The owned actual-game run `display-water-candidate-20261011-v53` completed both
underwater-up-near and underwater-up-moving phases and exited 0. The collector
verified pack identity, NVIDIA renderer and active Iris/no fallback, and archived
`candidate-runtime`. The native motion audit verified 58 PNG files, not their
visual quality. No images from this run were visually reviewed for acceptance.
`runtime-restored.json` proves byte-exact normal configs/Mods and unchanged ordinary
saves, with no save rollback and no instance-config change by the launcher.

CPU scope and quad-intersection tests pass; 15 runtime/diagnostic Python tests
pass; full Mod build and NVIDIA shader compile/link pass. Compile-only does not
dispatch, draw or read back. Full-goal completion and visual acceptance remain
unproven. Next integration needs actual atlas ownership/filtering/alpha and
first-visible-primitive attribution without borrowing the water-floor source.
