# Actual plant material GPU diagnostic v85

Owned NVIDIA/Iris run `display-water-candidate-20261011-v85`, request
`1510958a-8cda-4034-b311-4a6beef31f40`, completed with automatic quit and launcher
exit zero. Filtered receiver receipts are in `candidate-receiver-runtime.log`.
The exact opt-in pack gate alone enables this diagnostic; ordinary packs do not.

Actual model material vertices were checked against intersection packet
positions/UVs/primitive order before adding each model. Region aggregation
completed with 74 models / 1184 triangles / 10608 memberships, unavailable=0,
unloadedCells=0 and fresh owner-state validation. This proves those captured
models' correspondence, not complete model ownership of the whole trace region.
The retained `completeModelOwners=false` and `traceAdmission=false` are important.

Original captured receiver-source fragment GPU draw/readback used actual atlas,
decoded tint/lightmap/AO, world positions and geometric normals. Two first-model
material controls ran at frame 3 / resource generation 1:

| Model | Triangles | Samples | Opaque / positive | Transparent |
| --- | --- | --- | --- | --- |
| Tall seagrass, lower half | 16 | 240 | 72 / 72 | 168 |
| Seagrass | 16 | 240 | 48 / 48 | 192 |

Readiness matched independently read actual base-level alpha under the owned
magnification filter; transparent samples returned unready zero radiance.
`ReceiverSourceDraw` also required paired total/direct-Sun readiness and
nonnegative Sun bounded by total for every output. Total RGB sums were
0.12700062709336635 and 0.0776643208009773. Direct-Sun sums were only
3.533647767450798e-8 and 2.0337708711570812e-8, so this is not a robust positive
direct-Sun radiometry test. Upper tall-seagrass, kelp, other lighting phases and
nonzero texture gradients/LOD were not independently GPU shaded by this run.
The source fragment's existing full-alpha qualification remains conservative;
fractional-alpha cutout/mip coverage is not established by these samples.

The ordinary source producer also ran through the delegated top-point API,
but exact old/new output equality still needs a controlled payload/output test.
Plant material outputs are diagnostic only: they are not yet published into
the world-reflection lookup. No floor source is borrowed and no plant voxel is
treated as empty water. Natural reflection appearance is not fixed by this run.

Normal configurations/Mods and instance configuration were restored exactly;
the ordinary save is unchanged and no rollback occurred. See
`runtime-restored.json`. Recorded PNGs/timestamps are not temporal acceptance;
the full Sun/water/coherent illumination/performance goal remains open.
