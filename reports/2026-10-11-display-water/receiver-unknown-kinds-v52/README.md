# Unknown subtype v52 — vegetation coverage evidence, not a physical fix

The producer optionally annotates kind-zero cells with a subtype in the otherwise
unused height channel. Kind, geometry admission, source eligibility and readiness
remain unknown/zero. Normal captures still write zero tags. Live annotation is
gated to the exact v52 diagnostic ZIP name, not ordinary packs. Fresh validation
checks subtype drift as well as existing geometry/source guards.

CPU tests verify unloaded/outside rejection before a cell read; air, pure water,
seagrass, tall seagrass, kelp, other unsupported and unknown classifications;
unchanged unknown admission/no invented radiance; ordinary zero tags and fresh
subtype drift rejection. On actual RTX 3080 Ti, compressed DDA rejects all nine
tags, including an unknown tag with forged ready source channels. Retained
world-reflection/source-stage controls pass. The exact diagnostic shaders also
compiled/linked, separately from rendered guard tests. Six builder and nine
runtime safety tests pass. ZIP comparison changed only the diagnostic water
fragment and receiver library, leaving the original v50 ZIP unchanged.

The actual run used Mod v58, SHA256
`606e7c4d90d2924f08e01f443b6a1018409c36d6a6c1732cb9ad3201ff21b726`.
Mod v57 was built but never installed. Actual producer receipts confirm
`unknownKinds=true`, ready=2, 56376 records (still below 65536), 6748 sources,
14492 partials, 7246 air caps, 6777 mesh captures and 600146 geometry reads.
The added subtype distinctions split some previously merged unknown runs;
known geometry/source qualification was not widened.

## Palette and actual images

Only rejected unknown-geometry rays use subtype colors. Other rejection reasons
are dim neutral; non-TIR center is darker neutral. Qualified world source hits
remain green, screen-space reflection hits pale blue. Unknown subtype palette:

| Tag | Color | Actual producer classification |
| --- | --- | --- |
| 1 | Red | Unloaded |
| 2 | Pink | Outside world height |
| 3 | Blue | Unqualified air |
| 4 | Yellow | Unsupported seagrass |
| 5 | Orange | Unsupported tall seagrass |
| 6 | Magenta | Unsupported kelp/kelp plant |
| 7 | White | Other unsupported shape/material |
| 8 | Cyan | Unqualified pure-water cell |
| 9 | Purple | Unknown cell |

Actual static frame-026 and moving frame-028 were viewed. Yellow/orange vegetation
patches and magenta kelp patches are prominent among the rejected regions.
They give concrete evidence that treating these entire plant voxels as unknown
loses reflected receiver coverage in the selected natural views. They do not
establish exact per-ray frequencies, every wave phase or the cause of the whole
folded sky-window boundary. Deep-water transport/display conversion shifts
magenta toward purple; do not infer exact tags from hue alone or claim absence
of another subtype from these two stills.

Both scenarios completed and auto-quit; native-motion audit verified 56 PNGs,
owned launcher exited zero and Java stopped. Exact normal config/Mods and
unchanged ordinary saves were restored without rollback. Diagnostic timing and
colored images are not ordinary-renderer performance or appearance acceptance.

## Required next implementation boundary

Do not simply label plant voxels as empty/full water and skip them: the ray can
hit real leaf/stem geometry. A legitimate extension needs owned actual plant
model triangles/quads, texture-alpha intersection and first-object ordering,
plus real corresponding material/lighting. Transparent texels may continue to
the floor; opaque texels must stop at the leaf, not borrow floor/UP radiance.
Account for model offsets/spill into neighboring cells, water-volume/interface
qualification, incomplete models, resource/world/frame changes and unavailable
data. Preserve unknown rejection for unsupported/incomplete geometry.
Start with controlled first-leaf/transparent-hole/nearer-bank/unknown negatives,
then prove actual Sodium model/material capture and natural moving views.
The complete Sun, underwater-window appearance and usable performance goal
remains open; this checkpoint supplies diagnosis, not normal-runtime adoption.
