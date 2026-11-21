# Untonemapped underwater interface diagnostic v90

Actual Minecraft run `display-water-candidate-20261011-v90`, request
`79aa643a-2923-4371-aada-b5829bc6ee6b`, completed with owned launcher exit 0.
The corrected four-component clear-color directive passed actual Iris startup.
Both principal captures passed exact RGBA8 palette classification, without
unknown colors. This is interface-status evidence, not ray-vector readback.

Each principal capture contains 1,280,000 pixels:

| Status | Near | Moving |
| --- | ---: | ---: |
| Transmission | 1,214,896 | 803,517 |
| Total internal reflection | 62,750 | 474,951 |
| Transmission on wrong geometric side | 2,155 | 995 |
| Admitted downward transmission | 199 | 310 |
| Reflection on wrong geometric side | 0 | 227 |

The moving principal image was visually inspected. Wrong-side pixels are
localized around the fragmented boundary and detached small patches; their
small area does not establish that they explain the whole folded-sky defect.
Downward transmission records direction only, not a second surface intersection.
Earlier post-tonemapping dominance estimates missed the small reflection-side
failure; use the raw target for subsequent optical admission checks.

The ordinary configurations, Mods and ordinary save matched the baseline after
restore; no save rollback was performed. Main visual and performance acceptance
remain open. Next: reject or resolve wrong-side optical paths against the actual
geometric surface, then evaluate the remaining transmitted-sky mapping and outer
reflection separately; do not claim the diagnostic itself fixes the rendering.
