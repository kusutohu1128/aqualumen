# Cell publication v64 — immutable payload and controlled NVIDIA decode

`ReceiverPlantCellPublication` now serializes the authoritative spatial index
into padded RGBA float headers and membership links. A cell header contains
membership begin/count, full-water-column proof, and complete-model-owner proof.
These last two qualifications are independent: water behind a plant cannot by
itself make missing/incomplete geometry traversable. A missing proof writes both
flags zero. Empty membership does not imply full water or complete model capture.
The links retain original packet primitive IDs for later material attribution.

Both textures use width 256, with cell ordering x + width*(y*depth+z), matching
the existing receiver convention. Two footer texels follow the cells: window
width/height/depth/membership count, then primitive count and three zeros. These
prevent same-product wrong-window and forged-count decoding. Remaining padding
is zero/unqualified. The index retains
its existing 96×64×96 window, 1048576 membership and single-packet triangle limits.
This is data serialization, not GL allocation/binding; the existing small source
texture uploader cannot yet upload the largest payloads. Multi-model whole-field
aggregation is still needed beyond the current bounded packet.

Capture validates world/frame/resource identity before and after assembly. It
retains immutable per-cell witnesses, requires a fresh validation phase, and
re-reads every proof before returning any publication. Fluid/model proof drift
even within the same epoch rejects the whole payload. Provider implementations
must actually discard cached observations at beginValidation and establish
complete model-owner coverage; a caller-supplied true flag is not an independent
proof that every actual world model was captured.

`../plant-cell-publication-cpu-v63.log` verifies every emitted cell count/link
against authoritative candidate IDs, independent fluid/model flags, unavailable
proofs, defensive output copies, stale getter rejection, resource-epoch drift,
same-epoch fluid drift and same-epoch model-coverage drift. Earlier spill/boundary/
serialized-float/extent/capacity tests also remain passing. Full Mod build
`build/aqualumen-physics-0.3.0-plant-cell-publication-fresh-v73.jar` succeeds and is
not installed. `git diff --check` succeeds.

The shared `water_plant_cells.glsl` decoder is tested by uploading this actual
Java publication and drawing/readback on NVIDIA RTX 3080 Ti. Every cell span and
independent proof flag matches the CPU payload exactly. Malformed footer, span,
proof flags, primitive IDs, extra metadata, NaN, duplicate and reordered links
are rejected, as are wrong window dimensions and forged primitive counts.
Evidence: `../native-plant-cell-decoder-v64.log`. The proof provider is a controlled
fixture, not an actual-world completeness witness.

No actual-world completeness or visual improvement is claimed by this checkpoint.
No Minecraft client was launched or ordinary settings/saves changed. Next is indexed triangle lookup,
then actual owner-complete producer upload/binding and selected-leaf shading.
The opt-in DDA integration remains disabled in ordinary play; the full water/Sun
goal remains active and unachieved.
