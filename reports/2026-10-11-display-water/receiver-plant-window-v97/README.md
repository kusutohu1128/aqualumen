# Full receiver-window plant diagnostic v97

Actual run `display-water-candidate-20261011-v97`, request
`a3bc1a5e-27ef-4718-b4da-47b86f417752`, completed with owned launcher exit 0.
The plant scan covers the actual initial 87x36x87 receiver window, with a padded
89x38x89 conservative geometry index, instead of the former 17x15x17 probe.

4,042 model bounds were observed: 1,731 kelp-plant, 329 kelp, 1,618 tall-seagrass
and 364 seagrass blocks. The 16,384-triangle aggregate filled before all owners
could be retained. Only 1,310 models were retained; 2,732 captures were marked
unavailable. The retained 393,216 material attributes passed exact GPU readback,
and 119,784 memberships were indexed. All 272,484 scanned cell states were
validated; no scanned cell was unloaded.

This is authoritative capacity-failure evidence, not complete coverage. The
aggregate is diagnostic-only, explicitly completeModelOwners=false and
traceAdmission=false. It must never be admitted as a complete reflection field.
Increasing the old cap to 16,384 is insufficient for this actual scene.

Next use a bounded paged/tiled texture layout for the complete geometry/material
set, preserving exact per-cell membership and per-hit owner association. Do not
discard plants, shrink the actual reflection window, or relax completeness to
make the test pass. Capture still occurs once at initial location; later scene
locations need fresh coverage before actual reflection admission.

No beauty PNG or temporal visual acceptance was performed for this packet.
Ordinary configurations, Mods and save hashes matched after restore, without
save rollback. Full Sun/water/sky/motion/performance goals remain incomplete.
