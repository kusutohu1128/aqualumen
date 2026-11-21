# Actual owned Iris encoder output

The live owned Sodium invocation now copies the actual pinned Iris
XHFPTerrainVertex encoder output before its dedicated native buffers are freed.
At frame 2/resource generation 1, gravel (448,45,-384) supplied four packed
UV/color/light vertices with actual stride 28. Raw AO/light are retained alongside
the packed words. Color and the low two light bytes must match the captured
prepared inputs; no guessed UV quantization is substituted. `source-runtime.log`
records the actual cold-start result and source input size zero.

The observer reads only inside the thread-local owned renderer scope, verifies
the encoder pointer/stride/returned extent, and owns copied Java values. It does
not inspect ordinary worker buffers or submit a terrain mesh. CPU scope tests
also reject incomplete, mismatched and duplicate encoded captures and verify
list ownership. Native atlas/shared-source tests remain controlled footprint
tests, not shading of this particular live face.

The near-view run used NVIDIA/Iris without shader fallback. Native PNG/index
validation is separate from visual acceptance: no appearance improvement is
claimed here. Live lightmap matrix/UV shrink decoding, projected derivatives,
actual filtered source shading, paired radiance publication, partial surface
water and vegetation ray handling remain unqualified. The original goal stays
open; the source input size remains zero.

Experimental Mod SHA256:
`3ece2fdf7d57c2e2348b96b826b7c7c1cdf8949b84197881935fb4f43b03008c`.
The client exited normally. `runtime-restored.json` verifies exact normal config,
Mods, instance settings and ordinary-save hashes, without any save rollback.
