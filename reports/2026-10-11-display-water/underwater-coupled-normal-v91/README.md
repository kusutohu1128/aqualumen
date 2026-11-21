# Coupled interface-normal diagnostic v91

Actual Minecraft run `display-water-candidate-20261011-v91`, request
`ec94a5a4-7349-4593-86ec-be35392fa2a3`, completed with owned launcher exit 0.
Both 1600x800 principal captures passed exact untonemapped RGBA8 palette decoding.

| Status | Near | Moving |
| --- | ---: | ---: |
| Transmission | 1,196,854 | 812,294 |
| Total internal reflection | 83,001 | 466,939 |
| Admitted downward transmission | 145 | 767 |
| Transmission on wrong geometric side | 0 | 0 |
| Reflection on wrong geometric side | 0 | 0 |

The moving principal capture was visually inspected: fragmented transmission/TIR
boundaries remain, without red/orange wrong-side patches. World-downward rays are
still present and are not necessarily on the wrong geometric side of a tilted
triangle. No second-interface intersection has been established.

This confirms the coupled optical admission constraint for these captures only.
The v90 and v91 runs are not time-matched wave snapshots; changes in region size
must not be attributed solely to the correction. No beauty-render improvement,
temporal stability, energy-conserving transport, or performance acceptance is
claimed. The helper adjusts unresolved shading normals, not actual geometry or
self-occlusion. It remains explicitly opt-in through the comparison macro.

Ordinary configuration, Mods and save hashes matched the baseline after restore;
no save rollback was performed, and Java was absent. Next: beauty-render review
of the coupled correction and remaining sky-window/outer-reflection defects.
