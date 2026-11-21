# Indexed triangle selection v65

The shared intersection kernel now supports membership-link selection directly
against the original global triangle texture. It retains original primitive IDs
for later material attribution and does not create a per-cell copied packet.
The existing contiguous-packet entry points delegate to the same kernel.

Callers must validate the cell publication using `waterPlantCellSpan` and retain
independent full-water and complete-model qualifications before traversing an
unknown cell. The selector alone does not prove ownership or full water.

Controlled NVIDIA RTX 3080 Ti draw/readback checks in
`../native-plant-indexed-v65.log` cover a selected leaf with original global ID,
a transparent hole that must not borrow an excluded floor, an empty selection,
and an out-of-texture membership span. Existing alpha, interval, tie, malformed
geometry and GL-state restoration checks also pass. The Java publication decoder
is tested separately by the same command, not yet end-to-end with the selector.

No live world producer, ordinary-play binding, leaf radiance or Minecraft visual
acceptance is claimed. The opt-in production DDA hook remains disabled in normal
play. Complete model-owner aggregation and publication integration remain open,
as do the full water, underwater sky and Sun acceptance requirements.
