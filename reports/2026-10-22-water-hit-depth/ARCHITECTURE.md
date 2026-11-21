# First-hit depth consistency contract

The accepted primary water hit is one record containing point, view point, projected window depth and acceptance. Eligibility and derivatives remain raster-owned. Accepted hits write their projected depth; hardware late depth ordering selects visibility. Composite owns one eye attenuation operation reconstructed from the surviving depth. No opaque-depth guard preserves the old raster winner.

## Synthesis

The independent Claude and Codex designs both prefer hardware depth over a new transport-only MRT. Parent scores against `.audit/depth-arena-rubric-2026-10-22.md` are Codex (2,2,2,2,2,1) and original Claude (1,1,2,2,2,2). The original Claude opaque guard fails the mandatory visibility criterion. Actual Claude crossjudge withdrew that guard and agrees with the Codex visibility contract. Its evidence is `claude-crossjudge/RESULT.md`.

Graft Claude's baseline-plus-candidate observation chain and source-radiance scope limit. Do not move reflected-source incidentDepth in this unit. That existing raster-plane solar-entry approximation is R2 work, not repaired physical transport. Do not change wave evaluation, IOR, Fresnel, exposure, raster eligibility, trace surface-Y approximations or composite lighting at the eye.

## Caller and data shape

```glsl
struct WaterPrimaryHit {
    bool accepted;
    vec3 point;
    vec3 viewPoint;
    float windowDepth;
};
WaterPrimaryHit waterPrimaryHit(vec3 rasterPoint, vec3 solvedPoint, int solveStatus) {
    // not implemented in this sketch
}
```

At main entry initialize gl_FragDepth to gl_FragCoord.z on every path. A validated solved point overrides it. Require finite point/clip values, positive clip W, projected XY within 0.01 pixel of gl_FragCoord, and strictly in-range window depth computed using gl_DepthRange. Invalid projection retains raster point/shading/depth. No early_fragment_tests or conservative depth declaration. Exact opaque ties/quantization require observation and remain an explicit representational gate, not a raster-preserving occlusion guard.

Update initial straightPath from opticalViewPos and shadowVisibility from opticalPoint for accepted hits. Preserve all raster derivatives. Existing optical trace origins stay at the hit. Composite C0 formula is unchanged, but its input depth is corrected. No new producer or simulation writes.

## Isolated artifacts

The writer owns only new generator/helper/tests in `/tmp/aqualumen-depth-writer.lIYL1g`. Parent integrates after review and owns native tests, actual GPU/Minecraft lifecycle, qualification and restoration. Original shader sources, hit1 archives, observers and Evidence stay immutable. New outputs use exclusive creation and record every input/generated source hash.

Generate hit1d baseline and depth1 candidate from pinned hit1 control/paired archives. Baseline shading/depth remains hit1. Both paired packs add passive observation. C1 keeps raster point/mean. C3 becomes opticalPoint.xyz plus projected accepted depth, -1 ineligible, -2 projection rejected. C2 is post-composite actual distanceToEye/transmission RGB, with finite zero transmission outside the underwater branch. C12 and C13-C15 retain meanings. New observer schema/version explicitly replaces geometry/status meanings.

Keep depth0/1 active only in FINAL preview branches, with actual capture preview zero. Read single-component float depth with strict allowed depth formats, dimensions/base level and comparison mode; never weaken the RGBA32F color boundary. Preserve GL read state and verify all sampler bindings before/after FINAL. Exact source/program/pack/raw hashes bind analysis to captures.

Accepted observer-only deviation after actual fail-closed capture is recorded in DEPTH-STORAGE-ADDENDUM.md. Unsized GL_DEPTH_COMPONENT is admitted only with queried 24-bit unsigned-normalized storage, observed on this driver with the pinned Iris allocation. The new actual capture must confirm the same pair. Shader semantics and the visibility contract do not change.

## Verification

Native eight-MRT fixture attaches real D32F depth. Unobstructed hit1 must fail optical point/depth consistency, candidate must pass. Both opaque straddle directions must be exercised and corrected, plus a fully blocking ceiling. Render actual generated composite for eye distance and one Beer term. Native passivity compares each instrumented copy with its own control, not candidate with original C0. Native compile is not Iris attachment proof.

Actual same-FINAL near/deep captures add previously absent depth data. Baseline must match composite distance to raster and fail agreement with optical point. Candidate must match emitted projected depth to raw depth0, optical point distance to composite distance and transmission to Beer. Compare C1/depth1 byte-identically where scene stability supports it. Use a storage-format-specific depth budget and the declared bounded eye-distance budget. Report distance/error distributions. Do not infer a general horizon-distance precision bound or relax the budget after captures.

Before actual captures, the bounded eye-distance budget is declared as 0.001 m. This tests millimeter-scale consistency in these fixed near/deep poses, not two-ULP inversion or full radiometric accuracy. Report maxima and distributions as well as violations. D32F stored depth must equal emitted C3.w exactly. D24 storage may differ by one 24-bit quantum. RGB Beer comparison uses absolute 1e-6 float tolerance. No pixels are silently excluded because their depth disagrees.

Actual draw-state/opaque straddles, coverage outside raster mesh, headroom/contact containment, later translucents/hand, shadow radiance attribution, R2 source height, dynamic ripples, general worlds, visual acceptance and performance remain separately open unless observed. Test-only success is not production completion. Restore Lab 0.6/physics 0.2 and prove configs/mods/ordinary save unchanged at closure.
