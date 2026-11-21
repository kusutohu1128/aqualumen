# Actual plant owner bounds v96

Actual run `display-water-candidate-20261011-v96`, request
`278d4679-9627-4695-99af-c22eec36ad73`, completed with owned launcher exit 0.
The exact named pack enables the diagnostic only; plant reflection remains off.

At capture frame 3/resources 1, 74 models were retained: 68 tall-seagrass blocks
and six seagrass blocks. All 1,184 triangles were aggregated; 10,608 conservative
cell memberships were indexed. No capture was unavailable and no scanned cell
was unloaded. All 4,335 scanned block states were freshly checked, alongside
captured model owner states, including a final check after material GPU work.

Actual world-space packed vertex bounds relative to each owning block had
aggregate minimum [0,0,0] and maximum [1.0000009536743164,1,1]. No model exceeded
its unit cube by more than 1e-5. This tolerance accounts for packed vertex
quantization; index membership retains closed-boundary adjacent cells rather
than dropping potentially contributing triangles.

This establishes only the captured seagrass model extents. No kelp model was
present in the initial probe region. It does not prove all resource-pack models,
all neighboring owners, or coverage of later near/moving camera locations.
The one-shot probe currently samples the initial region, not each scene's
reflection field. Complete model-owner admission and live reflection remain
false. Next extend coverage capture to the actual receiver window/scene domain,
then build fluid/complete-owner proofs before admitting plant traversal.

No PNG visual review or temporal acceptance was performed for this packet.
Ordinary configurations, Mods and save hashes matched after restoration;
no save rollback was performed. Full rendering and performance goals remain open.
