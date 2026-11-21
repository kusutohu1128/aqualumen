# Fixed-density result and next causal slice

2026-10-03. CPU/source review and inspection of saved actual images; no new
GPU/game execution, shader implementation, live-pack change or shipping adoption.
This updates the direction, not the frozen evidence, in
[the prior representation plan](codex-underwater-bandwidth-tessellation-next.md).
The full water/sunlight realism goal remains open.

## Result: integration, not a visual fix

[Native v2](../../reports/2026-10-03-water-density/native-v2-controls/result.json)
measured 1/6/24 triangles, exact original corners, nonzero generated height, and
within-factor observer neutrality. The
[independent saved-TF audit](../../reports/2026-10-03-water-density/independent-native-v2-saved-tf-audit.json)
qualifies complete shared-edge sets and every mixed-third contributor, including
unadmitted interpolation under fixture-specific binary32 bounds. This accepts
bounded native geometry integration, not arbitrary natural-world boundaries.

Actual density4 near/deep/tilt captures and selected FINAL readbacks are in
[the density packet](../../reports/2026-10-03-water-density/EXPERIMENT.md).
Side-by-side inspection against saved level1 shows the ring/rim folds and dark
exterior substantially persist; no quantitative visual-quality or motion claim
is made. Each readback qualifies 16 selected known underwater TES-origin points.
[Near stage observation](../../reports/2026-10-03-water-density/iris-near-stage-attachment.json)
records VS/TCS/TES/FS and three-vertex patch arity. Three is not the density:
the ZIP's TCS requests outer/inner factor4 for constant water material, else1.
Selected FINAL sampler-role bindings are qualified; exclusive water-program/draw
binding, actual Minecraft primitive counts, and natural factor4 generated
geometry remain unproven. Post-Iris stage hashes are not ZIP-file hashes, and
PNG/raw same-frame identity is not accepted. Thus unchanged still appearance
does not prove geometry irrelevant or establish the folds' cause.

## Verified source facts

- [Production VS](../../shaders/gbuffers_water.vsh) and density TES evaluate
  existing height with footprint0/detail0; subdivision changes sampling, not
  the spectrum. Original corners and topology admission stay protected.
- [Known FS normal](../../shaders/gbuffers_water.fsh) uses detail1 with
  `max(1.25*footprint,.035)`, local bathymetry and exact unknown-weight0.
  Unknown water retains its raster facet. Ripple and grazing/orientation rules
  are separate existing modifiers.
- [Wave model](../../shaders/lib/waves.glsl) uses
  `geometricDetail=1-smoothstep(2,5,k)` at detail0: full through k=2, tapered to
  zero at k=5 (wavelength about 1.26 m). Detail1 retains those short modes subject
  to pixel filtering. Full-spectrum normalization is independent of detail.
- `unresolvedVariance` contains `weight²*k²*.5*(1-bandlimit²)`, not lost
  geometric-detail variance. Changing detail alone leaves that scalar formula
  unchanged. Final-normal derivatives and computed roughness do change with n.
  Current underwater output uses neither the roughness-filtered reflected sky
  nor the above-water solar lobe; it does not integrate residual slopes through
  underwater Fresnel/TIR/transmitted sky. The transmitted sky lookup is not a
  convolution over an unresolved normal distribution.

## Ranked next experiment: one analytic-normal bandwidth variable

1. First test representation mismatch: keep one qualified fixed geometry pack
   (prefer the latest factor4) in both control and TEST; change only the known
   underwater upper-interface analytic slope evaluation from detail1 to detail0.
   Keep footprint, phase, bathymetry/unknown guards, ripples, and existing final
   orientation/grazing logic. Use continuous analytic slopes, not flat facets.
   Leave air-side behavior, exposure, IOR, variance policy, transport/trace laws,
   miss fallback, clouds and density untouched. This is a diagnostic cutoff, not
   reciprocal physical water. Changed normals necessarily change Fresnel/TIR,
   rays, normal-offset shadows/SSR and possibly receivers; unchanged laws do
   not mean unchanged outputs or numerically unchanged computed roughness.
2. If a qualified bandwidth change does not address it, isolate
   critical-angle/environment filtering next; the current transmitted sky is
   evaluated for one resolved normal rather than a residual normal distribution.
3. Offscreen-reflection/miss representation is a separate later causal slice,
   not permission to inject sky or brighten the dark exterior.

Before visual attribution in the first test, retain the prior finite-endpoint
check of detail0 slopes against original VS height differences (.01/.02 m):
uniform known columns, zero depth gradient/ripples, fixed phase, unclipped
samples and inactive grazing correction, with finite-endpoint
float/transcendental uncertainty. Then qualify passive observation, control
repeats, pre/post final-normal changes and the same near/deep/tilt views. Fewer
fine folds with qualified normal changes supports a bandwidth contribution,
not sole cause or visual acceptance; no change moves attention away from it.

## Longer-term physical operator, distinct from the cutoff

Design a common resolved mean surface plus a consistent residual slope
distribution/covariance, avoiding double-counting and retaining depth-gradient
terms. Couple geometry/normal filtering and residual bookkeeping; integrate
that distribution over reflected and transmitted directions, Fresnel/TIR and
visibility for both interface directions. A scalar roughness increase or
discarding short waves is not that operator, especially where current underwater
roughness has no active output consumer. This proposal requires new numerical,
energy/reciprocity and image evidence; it is not implemented fluid conservation,
physical self-occlusion, offscreen geometry or full physical realism.

Verified unchanged production SHA256: VS
`16554f88edf3519481447f22f44b18a06c40881a27504b81e67b58efab266df0`,
FS `8dfae28a5a98d5c9be4a0e39488cdfe66a01440d2123fd786e83e3e3fcfc0b18`,
waves `4fc71a62459fde55261a68217d4d18d715cd2b678274af1b6c8812ebd3153191`.
