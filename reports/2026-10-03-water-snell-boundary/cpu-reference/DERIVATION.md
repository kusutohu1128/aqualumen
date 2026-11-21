# Independent CPU support reference

The reference does not import `light_kernel` or a shader implementation. It treats the recorded binary32 `v` as-is. The raw target `t` is retained, and only its physical **direction** is normalized in Decimal, explicitly; neither the recorded view vector nor its norm is repaired.

Write `u=t/|t|`, `k²=1+η²(|v|²−1)`, `A=k u+ηv`, and `n=A/|A|`. The admitted inverse branch requires downward view and facet, upward target, `n·v>0`, `n·u<0`, and positive forward discriminant `D=1−η²(1−(n·v)²)`. The independent forward expression is `−ηv+(η(n·v)−√D)n`. On this branch it must reconstruct `k u`, not a silently unit-normalized view result. For exact-unit view `k=1`; raw binary32 norm error is preserved through `k` otherwise.

Slopes are `s=(-A.x/A.y,-A.z/A.y)`. Differentiating this ratio on the unit target sphere gives `|ds/dΩ_u| = k² |A·u| / |A.y|³ = k² |n·u| / (|A|² |n.y|³)`. This is an analytic mapping quantity, not a measured GPU kernel or integration/energy proof. The forward discriminant is evaluated separately rather than replaced with the squared transmitted-dot identity.

The raw-cosine Fresnel algebra uses independent s/p ratios. Its transmitted fraction is evaluated by the positive product expression, not subtraction `1−R`, avoiding critical-limit cancellation; it is labelled raw-cosine algebra, not a physical calibration of nonunit incident vectors.

Both 80- and 120-digit results must agree in support sign and all mapped numerical fields at the fixed absolute-plus-relative `1e−60` policy. Invalid input/domain and singular inverse states remain distinct from a finite geometric no-preimage branch. Three explicitly sequenced nearest-even binary32 replays describe possible arithmetic models, not NVIDIA compiler behavior.

The predeclared `j=12..20` up-target family contains nine supported-side numeric rejections, including `j13` with positive Decimal discriminant about `3.40933e−8` versus unfused binary32 zero. Its nearly horizontal facets do not establish nonzero Gaussian solar transport, a production shader RED, or any natural-scene improvement. No shader, GPU, game, or existing evidence was changed.
