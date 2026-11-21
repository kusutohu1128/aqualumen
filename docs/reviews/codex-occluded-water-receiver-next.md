# Occluded refracted receiver: implementation direction after real coast evidence

2026-10-06. Design based on actual MAIN world rays, not an adopted renderer change.
Full requirements remain `docs/REALISM_GOAL.md`; this slice does not replace them.
See `reports/2026-10-06-water-coast-world/` for source, live raw and saved geometry.

## Qualified finding and limits

The earlier9->32 upper-surface iteration ablation recovered0 of8 dark receivers.
The actual original-MAIN world-origin/direction witness now produces16 supported
first-sand intersections in independently decoded saved Minecraft1.21.1 terrain.
All8 dark points' physical first receiver is blocked from the ordinary straight
camera ray by a different nearer sand cube. All8 adjacent bright controls reach
the same first cube on that camera ray. Refracted and camera traversal block
states agree across two closed saved snapshots. No noncube/cutout was encountered
on these selected rays; reader controls reject them rather than invent geometry.

This establishes bounded point-center full-cube occlusion, not full frame-frozen
geometry, finite depth-texture pixel footprints, all shoreline root causes or
production improvement. It explains why more screen-depth iterations are not
sufficient here. Do not turn valid screen-space misses into forced hits or
retrieve the farther visible floor behind an opaque first object.

## Chosen next implementation path

Introduce a conservative, world-anchored opaque receiver representation through
the existing optional read-only client bridge. Keep the normal0.6/physics0.2
handoff unchanged until the new path qualifies. Initial controlled implementation
can support full-cube terrain with explicit unknown/noncube handling; arbitrary
block shapes and temporal naturalness remain full-goal work, not declared solved.

1. Write a failing production-MAIN regression at the actual seam: a refracted
   first floor exists but is occluded in camera depth. Supply independent known
   geometry/material/light inputs, not a fixture whose expected hit is selected
   by the shader search. Preserve near closed-bank FIRST vs colored BACKGROUND
   negatives and unready/out-of-bounds/unsupported controls.
2. Extend the loaded-world bridge with a bounded receiver snapshot, using only
   already loaded chunks. `Bathymetry` currently supplies bilinear depth/surface/
   validity and has a reserved channel; that is NOT complete opaque occupancy,
   arbitrary geometry, albedo or radiance. Do not pretend its smooth column depth
   is the actual stepped first surface. Keep existing wave geometry/optical
   spectrum, camera-relative grid convention and frame-consistent updates intact.
3. Implement a conservative full-cube ray traversal against the snapshot, with
   explicit air/water/opaque/unsupported classes, first-object identity, surface
   normal, material and readiness. A sliced2D representation fits the existing
   Iris dynamic sampler pattern without assuming a new3D sampler API. Verify
   actual limits/units/format/allocation on NVIDIA and Iris; do not hardcode a
   supposedly free texture unit or corrupt caller GL/UNPACK state.
4. Source appearance must come from actual vanilla material/atlas UV/tint and
   lighting data or the same world-space terrain-lighting model, not a guessed
   sand color or another pixel's RGB. Validate actual model/material extraction
   through the pinned1.21.1/Iris1.8.8 runtime. Unsupported geometry/materials must
   retain a qualified conservative fallback. No purchased/copied shader assets.
5. Keep dry receiver radiance and direct-Sun attribution separate, as C4/C8 do
   today. Apply incident water-entry Fresnel/Snell/Beer, caustic attribution and
   the separate outgoing/radiance-index convention exactly once. Match world
   receiver normal/shadow/ambient/source units to visible screen-hit controls;
   do not feed a pre-attenuated source into another full Beer operation.
6. Join screen and world paths by independently confirmed first-object/source
   identity and separately transported radiances, not blended UV/path estimates.
   Retain closed-bank, foreground, viewport, unsupported, same-surface and bounded
   travel protections. Visibility absence does not imply an emissive sky source.
7. Validate actual coast dark/bright pairs, shallow/deep/shore, above/below,
   changing camera/weather/contact motion and all affected retained production
   controls. Native GL/source math is not Iris allocation or Minecraft visual/
   timing proof. Restore safe normal play after each authorized TEST cycle.

## First deliverable for the next goal turn

Build the failing occluded-first-receiver production fixture and a pure bounded
receiver-snapshot/traversal contract, cross-checked against the actual saved16
world rays and independent oracle. Then implement the smallest conservative
world geometry/material source path that satisfies that real fixture without
breaking the closed-bank negative. Do not spend another turn rerunning the32
budget experiment or calling a cosmetic proxy blend a physical correction.

This is useful geometric/optical receiver work, not mass-conserving fluid motion.
Cloud/Sun/Moon/volume transport, arbitrary shapes, moving highlights/wakes and
the complete natural visual goal remain active acceptance requirements.
