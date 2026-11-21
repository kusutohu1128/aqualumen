# Raw underwater reflection-source attribution v93

Actual run `display-water-candidate-20261011-v93`, request
`69dbb271-acf0-49c6-aada-e78a72e282e2`, completed with owned launcher exit 0.
The diagnostic writes exact RGBA8 outcomes before tonemapping to unused C12.
Its colors classify only Fresnel >= 0.9999; gray does not classify other rays.
The ordinary optical normal is retained, without the coupled comparison macro.

Exact principal PNG RGB counts, 1,280,000 pixels per image:

| Outcome | Near | Moving |
| --- | ---: | ---: |
| Gray (13,13,13): not the pure-reflection diagnostic subset | 961,265 | 761,387 |
| Red: world receiver attempted, no known first geometry | 123,507 | 325,800 |
| Green: world receiver's own radiance ready | 152,596 | 155,295 |
| Yellow: known first geometry, own radiance unavailable | 42,632 | 37,518 |
| Blue: screen-space reflection hit | 0 | 0 |
| Magenta: world receiver not attempted | 0 | 0 |

All pixels match this palette; no unknown RGB values. The moving principal image
was visually inspected. The exterior alternates between red, green and yellow
regions around fragmented gray transmission regions. Thus it is not uniformly
a screen-space miss: world-source admission and unavailable geometry/radiance
boundaries are directly implicated. The diagnostic does not determine the exact
rejection reason, identify each material, or prove that admitting currently
unavailable sources would fix the polygonal exterior. Never fill unknown rays
with arbitrary bright sky; below-water reflected rays require water-side sources.

Next determine world-ray rejection reasons for red regions, keeping source-ready
and known-but-unavailable regions distinct. Sky-window distortion remains a
separate unresolved issue. Main visual, temporal, performance and Sun-size
acceptance remain open. Normal configurations, Mods and ordinary save matched
the baseline after restore; no save rollback was performed.
