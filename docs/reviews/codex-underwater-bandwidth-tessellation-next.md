# Next underwater representation slice

2026-10-03, Codex source/bytecode review and TEST-only actual Iris observations.
Not a new Claude/Opus/Sonnet review, implemented tessellation, or shipping fix.
The full water/sunlight realism goal remains open.

The phase120 shared-atlas ablation is recorded in
[the checkpoint](../../reports/2026-10-03-underwater-facet/EXPERIMENT.md).
Root reviewed near/deep/tilt images from both actual packs. Replacing only the
known-column optical normal with the existing displaced raster facet substantially
changes the fine rim folds, but exposes coarse triangle seams, especially deep.
The dark exterior remains. The facet replacement is diagnostic, not an adoption.
Raw-data qualification and visual observations must remain separate.

## First isolate representation bandwidth

Current VS evaluates `localWaveState(..., detail=0)` on the vanilla mesh. This
removes modes with k>=5 while the known FS uses detail=1 with only pixel-footprint
filtering. The residual variance currently includes pixel-filter loss, not the
detail cutoff loss. Underwater roughness is not an integrated distribution of
Fresnel/TIR and transmitted sky directions. Thus merely lowering the optical
normal bandwidth is not microfacet-energy transfer or a complete physical model.
An underwater-only normal rule also does not establish a reciprocal interface.

The next native regression should distinguish continuous displacement-model
consistency from exact piecewise-raster normals. Use uniform deep known columns,
zero depth gradient/ripples, fixed phase, unclipped samples and inactive grazing
correction. Read original VS heights at center +/- epsilon in X/Z, reconstruct
the finite-difference slope/eye-oriented normal independently, and retain the
original FS observation/control. Use epsilon .01 and .02, with endpoint input
and output artifacts. Qualify the comparison before changing production.

For N=24 and WAVE_HEIGHT=.12, a conservative detail0 amplitude sum is .415692
and third-derivative sum bound is 51.961524. Each central-difference axis has
truncation bound M3*epsilon^2/6 plus endpoint-height uncertainty/epsilon. Include
pixel-filter difference (p=.035 gives a conservative vector bound .0158525),
float/storage errors, and actual sine/phase behavior. Gamma512 alone does not
bound all GPU transcendental error. A test-only parameter export may permit an
independent CPU64 Fourier reference for the finite endpoint set; do not promote
observed endpoint error into an all-coordinate/all-driver proof. Preserve
removable STORE-only C0 neutrality and original repeat controls.

The physically coherent longer-term operator separates a common resolved mean
from residual slope variance, then integrates that unresolved distribution at
the interface. Mean and variance are coupled representation outputs, not an
exposure adjustment. Do not adopt flat facets or claim that a one-line detail
change completes realistic water. Keep geometry density out of this bandwidth
experiment.

## Separate geometry-stage integration test

[Iris's program documentation](https://shaders.properties/current/reference/programs/overview/)
supports gbuffers triangle tessellation through `.tcs`/`.tes`, requiring the
[tessellation feature flag](https://shaders.properties/current/reference/shadersproperties/flags/).
These primary documents were checked on 2026-10-03. A read-only installed-JAR
review also found ProgramSet stage loading, SodiumPrograms stage connection,
SodiumShader tessellation state and the draw-device GL_PATCHES switch. This is
an available implementation seam, not successful runtime execution of our pack.

Pinned JARs: Iris SHA256 b5ad39a6cb113ca0a1765f06689f9f4b29ccd0c81247de90b06c42f5da1092f5;
Sodium SHA256 411c4c03167066f0e2e61ba17793b4be13ddd73de5b677c6d402f1d8f4262ac2.

First build an isolated level-1 pass-through TCS/TES diagnostic, keeping all
position, UV/lightmap, vertex color, normal, mean-height, unknown-weight and
material fields equivalent. Verify actual stages, three-vertex patch arity,
draw/depth/C0/diagnostic behavior before factor 2 or 4. Water/nonwater, negative
top winding, thin bottom, mixed unknown vertices and both triangle windings
must remain protected. No new renderer Mod is needed merely to test this seam.

Important validation hole: current `tools/glcheck.cpp` links VS+FS and its
compile-only mode does not attach or validate TCS/TES. Add an isolated multi-stage
draw/link check or a properly bounded extension before claiming native acceptance.
Adding subdivisions to already displaced VS positions produces only smaller
planar triangles. Any finer wave height must be evaluated at generated positions,
with original primitive topology admission retained and without inventing column
knowledge at a generated center. Fixed factor 4 still cannot resolve the entire
roughly .1m spectral tail. Do not mix adaptive LOD into the first experiment.

Chunk edges, side/top seams, vanilla varying corner heights and transparency
sorting remain risks. Geometry subdivision does not restore offscreen SSR
receivers, fix critical-angle cloud integration, conserve simulated water mass,
or change game collision/water levels. The dark miss fallback is a separate
causal slice; do not disguise it by inserting sky or lifting exposure.

Source at this checkpoint: water VS 16554f88edf3519481447f22f44b18a06c40881a27504b81e67b58efab266df0;
water FS 8dfae28a5a98d5c9be4a0e39488cdfe66a01440d2123fd786e83e3e3fcfc0b18;
shipping0.8.6 ZIP 16a7da88b7a5ba11d6aadfd56c717875fc61153b81cc859b4503da620c56c9d0.
No production geometry/bandwidth implementation was made in this slice.
