# Density experiment admission plan, not implemented

Read-only review, 2026-10-03. Implement only after level-one native and actual
Iris qualification. This is a distinct geometry-density variable, not an optical
normal bandwidth/IOR/exposure experiment or a physical fluid simulation.

Keep the original VS height/ripple evaluation unchanged. Add an exact 0/1
admission field only at the existing inner top-admission branch; do not reinterpret
the generated point's mean-height `fract`. At generated points restore the
undisplaced Y from `waterMeanSurfaceY`, then reevaluate the existing detail-zero
known/fallback height and existing ripple condition/clamp. Original corner
endpoints must retain their original VS clip/world outputs exactly.

Knowledge and admission are conservative over only barycentric contributors
with nonzero weight. An unknown or unadmitted third corner off a shared edge must
not change that edge. Generated local-column success alone cannot invent corner
knowledge. Failed knowledge retains the established fallback and exact unknown
weight one; successful knowledge yields exact zero.

For reversed shared edges, order the undisplaced endpoints canonically and use
the same `A+t*(B-A)` evaluation. Factors two/four have dyadic edge weights. Native
observations must still establish actual endpoint/shared-edge clip/world/depth
agreement; this reasoning is not a numerical all-coordinate proof.

Do not select patch density with an all-three-corners admission/known test: two
adjacent patches could select incompatible outer levels. The first diagnostic
should at least use the same fixed density for every water material triangle,
leaving unadmitted generated positions on the original displaced interpolation.
Nonwater remains level one. No adaptive LOD is included.

Minimum later fixtures: oppositely ordered shared edge, third-corner unknown
neighbor, mixed admission, thin bottom, source/flow sloped top. Observe actual
geometry, depth, knowledge and fallback separately. Side/top attachment remains
unresolved because sides retain their existing undisplaced geometry. Conservative
fallback can also produce an abrupt shape change near unknown regions. These
are explicit non-adoption boundaries, not solved by density matching.

Detail-one FS slopes, unresolved-slope Fresnel/transmission integration, dark
offscreen reflection misses and cloud-footprint behavior remain unchanged.
