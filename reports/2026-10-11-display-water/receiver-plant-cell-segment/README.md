# Plant cell index/segment v60 — controlled integration prerequisites

`ReceiverPlantCellIndex` builds immutable cell-to-triangle candidate spans from
the exact serialized float geometry uploaded to the GPU, not original doubles
or just the block-owner position. Conservative triangle AABBs include every
overlapped cell and both sides of closed integer-coordinate boundary contacts.
An uploaded float rounding onto a voxel boundary therefore cannot escape the
index. Extra candidate triangles are allowed; the GPU intersection remains the
actual geometry test, not an AABB hit.

The index is tied to the packet's world/frame/resource epoch, rejects lookup
outside its validated window, and rejects whole captures which would crop any
geometry/boundary contact or exceed membership capacity. Bounds match the existing
maximum 96×64×96 receiver window; membership storage is bounded to 1048576.
These are index capacity limits, not proof that every model in a world was captured.
This version indexes one packet (maximum 512 triangles). Aggregating all models
and proving producer coverage of owners outside the window remains required.

`ReceiverPlantPacket.select` copies a cell's exact primitive subset while retaining
epoch, reference coordinates and qualification. Duplicates/out-of-range/empty
selections reject. The caller must keep the corresponding original primitive ID
array for later material attribution; the selected packet's local primitive IDs
are not the original global IDs.

`waterPlantFirstSegment` extends the same shared GLSL kernel with a closed minimum/
maximum travel interval. It cannot choose an earlier/later candidate outside the
current DDA segment or an opaque-bank travel limit. Invalid intervals fail closed.
The previous whole-ray API remains a wrapper with minimum travel zero.

Evidence:

- `../plant-cell-index-cpu-v60.log`: spill into adjacent owner cells, sampled
  serialized triangle coverage, closed face contacts, float-rounding boundary,
  immutable membership/subsets, epoch, coordinate, truncation and capacity tests;
- `../native-plant-cell-segment-v60.log`: fresh RTX 3080 Ti shader draw/readback
  verifies entry/exit interval behavior, invalid interval rejection, and drawing
  an indexed subset which excludes a remote model. Existing hole/leaf/unknown,
  explicit LOD/filter, normal and hostile GPU-state restoration cases pass;
- full Mod build `build/aqualumen-physics-0.3.0-plant-cell-segment-v69.jar`, not
  installed; `git diff --check` passes.

An empty candidate list means only no geometry from the supplied packet overlaps
that cell. It does not qualify the cell as water, prove complete world/model
capture, admit an interface crossing, or supply source radiance. Unsupported,
unloaded, incomplete and unqualified-fluid cells must still stop the receiver
trace. No production receiver-cell reclassification or water shader publication
is made here. No Minecraft client was launched for this checkpoint; actual
natural scenes, performance and full water/Sun goal acceptance remain open.

Next: publish an all-model conservative index with actual fluid-volume ownership,
feed cell segments to the GPU kernel during the existing DDA, and attribute/shade
the selected leaf rather than borrow a cube UP source. The original opaque/unknown/
interface ordering must remain authoritative until that joint path is verified.
