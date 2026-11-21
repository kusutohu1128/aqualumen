# Raw unsupported-cell subtype attribution v95

Actual run `display-water-candidate-20261011-v95`, request
`7e0aa93a-fdbe-4ba4-a4a5-6ec3b86c5118`, completed with owned launcher exit 0.
The diagnostic Mod enables unknown tags only for the exact named diagnostic ZIP
and the retained v52 diagnostic; ordinary unknown-cell admission is unchanged.

Exact raw principal RGB counts, 1,280,000 pixels each:

| Outcome | Near | Moving |
| --- | ---: | ---: |
| Not pure-reflection subset (13,13,13) | 1,165,858 | 815,916 |
| Source ready (0,255,0) | 36,891 | 163,455 |
| Unsupported tall seagrass (255,89,0), tag 5 | 64,394 | 81,254 |
| Unsupported seagrass (255,255,0), tag 4 | 6,908 | 9,580 |
| Unsupported kelp/kelp plant (255,0,255), tag 6 | 14 | 136,363 |
| Water classification unavailable (0,255,255), tag 8 | 0 | 759 |
| Other rejection (25,25,25) | 5,935 | 72,673 |

All pixels match this outcome palette. Tall seagrass and kelp dominate the
unsupported-cell subtypes in these captures. Neither unloaded/out-of-height
tags nor unsupported air was observed. This is quantitative diagnostic evidence,
not visual acceptance; wave snapshots differ across v93-v95 and counts are not
matched causal area measurements.

The missing plant receiver path is therefore directly relevant, not an adjacent
feature. A correct repair must intersect actual plant triangles, respect alpha
cutouts and supply that primitive's own material radiance, while admitting empty
plant texels as continued water traversal. Treating entire plant cells as empty
or opaque boxes would not satisfy the goal. Existing material/GPU infrastructure
is not yet complete live owner coverage or actual reflection integration.

Normal configurations, Mods and ordinary save hashes matched after restore;
no save rollback was performed. The visual, temporal, Sun and usable-performance
requirements remain incomplete.
