# Region model capture diagnostic v68

The existing exact-pack-gated plant diagnostic now attempts every supported plant
owner in its loaded 17×15×17 search volume, rather than using one model per block
ID as its only geometry intake. The per-kind detailed alpha/GPU diagnostic remains
limited to one example to avoid repeating that expensive sampling for every model.

Packets use a shared camera-region reference and retain actual decoded geometry.
Retained triangles are bounded to 4096 before insertion. Failures and unloaded
cells are counted explicitly. After capture, actual owner block states are reread,
chunk identities are freshly validated, and the epoch is checked before reporting
the aggregate and closed-boundary spatial memberships. Geometry spilling beyond
the padded index window is rejected, never silently cropped.

This is diagnostic intake only: completeModelOwners=false and traceAdmission=false
remain explicit. A bounded plant scan does not prove coverage of unsupported
models, external owners or changed previously empty cells. Ordinary DDA admission
and source shading are unchanged. No live run or visual improvement is claimed.
`../plant-region-build-v68.log` records the full Mod compile; its uniquely named
artifact is not installed. CPU and controlled NVIDIA regressions are separate
evidence, not proof of actual region capture. Full water/sky/Sun acceptance is open.
