# Raw reflection rejection reasons v94

Actual run `display-water-candidate-20261011-v94`, request
`a74a6ee1-9a52-4b18-b88f-e8f5a96c54b5`, completed with owned launcher exit 0.
Exact untonemapped principal RGB counts, 1,280,000 pixels each:

| Outcome | Near | Moving |
| --- | ---: | ---: |
| Not pure-reflection subset (13,13,13) | 961,265 | 743,850 |
| Source ready (0,255,0) | 152,596 | 170,648 |
| Unsupported cell kind, reason 17 (0,0,255) | 123,493 | 261,956 |
| Source index absent, reason 9 (153,0,229) | 21,647 | 3,975 |
| Cached face differs from hit normal, reason 42 (255,255,255) | 20,985 | 33,933 |
| Leaves receiver grid, reason 6 (255,0,0) | 0 | 58,566 |
| Exceeds 48m, reason 20 (255,89,0) | 0 | 3,699 |
| Segment not below both surface facets (0,255,255) | 0 | 2,692 |
| Surface corners unavailable (255,255,0) | 0 | 351 |
| Other source/face admission checks (255,0,127) | 0 | 296 |
| Exact-boundary origin or exhausted traversal (89,89,89) | 14 | 34 |

Reason mappings were checked against the actual instrumented shader. Unknown
cell-kind rejection is the dominant unavailable-geometry reason in these views.
The face mismatch rejects a cached radiance for a different material face; simply
disabling that guard would make the reflected source physically incorrect.
Likewise, missing indices cannot be replaced by invented material colors.
Grid departure is important in the moving view but is not the near-view cause.

Next identify the original classification metadata for unsupported cells and
provide the correct hit-face source where currently only another face is cached.
This is pixel-count evidence, not visual review of these diagnostic images and
not a beauty-render fix. Main sky-window, sunlight, motion and performance goals
remain incomplete. Ordinary configuration, Mods and save hashes matched after
restore; no save rollback was performed.
