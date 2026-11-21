# Plant fluid ownership v61 — actual full-fluid observations, no plant admission

`ReceiverWaterVolume` separates fluid-volume observations from visible receiver
geometry. Full volume requires an already-loaded cell, actual water fluid kind,
finite height exactly 1, empty collision, nonempty state identity and one of the
exact supported water/plant IDs. A three-cell column requires all three proofs.
Partial/unknown height, collision, lava/other fluid and unrelated waterlogged
blocks remain unqualified. Full fluid does not classify a visible plant as empty
water or grant a receiver source.

`LoadedReceiverWorld.waterVolume` reads pinned actual block/fluid state, height,
collision and registry/state identity from only existing chunks. The diagnostic
compares the actual lower-cell state with the captured Sodium model state. There
is no production change to fullWater() or unsupported-plant trace admission yet.

A relevant preexisting cache ownership gap was also corrected: phase validation
cleared cell/height caches but kept the original loaded-chunk references without
freshly querying the chunk manager. `ReceiverChunkLease.validate` now re-reads
every retained section using the same FULL,false already-present lookup. Any
pointer replacement, disappearance or unavailable-to-present transition aborts
publication; identity comparison is by reference, not value equality. It does
not request generation or silently retain an unloaded chunk as current. The
source world's beginValidation executes this audit before its existing fresh
per-cell comparison. Ordinary geometry classification/source eligibility remains
unchanged. This implementation verifies leases before publication, not at every
subsequent draw, and cannot by itself prove all renderer/resource/light ownership.

Actual disposable Lab initial-terrain frame 3/resources 1:

- tall_seagrass at 449,47,-392: heights 1,1,1; fullColumn=true;
  modelStateMatch=true; traceAdmission=false;
- seagrass at 449,47,-390: heights 1,1,1; fullColumn=true;
  modelStateMatch=true; traceAdmission=false;
- actual GPU model probes retain 152 clear/88 visible and 160 clear/80 visible
  out of 240 diagnostic rays per plant, with 0 unknown, explicit point LOD 0;
- probe chunk-pointer validation succeeds; following primary source publication
  remains ready=2, 55983 records and 6748 sources with unknownKinds=false.

Evidence:

- `../water-volume-cpu-v61.log`: full-fluid/partial/collision/identity negatives,
  plant geometry still unsupported, fresh pointer reads, unload/replacement/null
  transition/value-equal identity/thread controls;
- existing geometry method, source-volume, field, run-layout/radiance and source
  composition CPU tests pass;
- `../native-plant-before-fluid-v61.log`: actual NVIDIA shared-kernel/subset/
  interval and GPU-state controls, not live unload or production plant DDA;
- 15 runtime/diagnostic Python tests pass;
- native shader compile/link is retained in `../native-plant-fluid-compile-v61.log`,
  explicitly not draw/readback or visual acceptance.

Mod `build/aqualumen-physics-0.3.0-plant-fluid-ownership-v71.jar`, SHA256
`d856d7aa713c0b3df1aca8fcd7f6ad57166b75fb23dcfde68d7aae095b74a6a1`;
pack `dist/Aqualumen-DisplayWater-PlantFluidOwnership-v61-2026-10-11.zip`.

The actual run `display-water-candidate-20261011-v61` completed static/moving
underwater phases and owned launcher exit 0. Collector verified NVIDIA renderer,
exact pack identity and active Iris/no fallback. `candidate-runtime` and
`candidate-receiver-runtime.log` retain evidence. Native audit verified 60 PNG
files, not visual quality; no images were visually reviewed for acceptance.
`runtime-restored.json` proves exact normal configs/Mods and unchanged ordinary
saves, with no save rollback or launcher change to instance config.

Actual unload/replacement/resource-reload controls and kelp observations remain
unverified. The full-fluid observation is a prerequisite, not proof that the
water-interface segment is admissible or that all overlapping model owners were
captured. Next integration must jointly publish complete model/spatial coverage,
fluid proof and material/source ownership and consume them during the existing
DDA. Ordinary unsupported plant cells must not be skipped merely because this
diagnostic observes continuous water behind their geometry.
