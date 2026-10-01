# Actual Claude Sonnet implementation contribution

2026-10-01, Claude Code 2.1.284, requested `--model sonnet`, actual responding model **`claude-sonnet-5-5`**. One successful turn, 20.416 seconds. No tools, repository access, unrelated project data or credential content were supplied to the model. The task was a small implementation patch, not an independent performance review.

The generated patch computes the cloud angular footprint analytically from the LUT UV gradients **before** the reserved solar-row branch, then passes it to the volumetric cloud helper. The helper no longer computes fragment derivatives after non-uniform early returns. Separate azimuth/elevation texel scales support the non-square LUT and polar latitude mapping.

Codex inspected the diff and applied it through `apply_patch` to `shaders/prepare.fsh` and `shaders/lib/clouds.glsl`, then ran the actual NVIDIA compilation and numerical GPU checks. Sonnet explicitly stated it had not compiled or run the patch; runtime validation is Codex's responsibility. Raw CLI response and task-scoped prompt are preserved locally in ignored `build/reviews/`, while sanitized model/result evidence accompanies this report.

The correctness rationale is supported by the [Khronos GLSL specification](https://registry.khronos.org/OpenGL/specs/gl/GLSLangSpec.3.30.pdf): fragment derivatives inside non-uniform conditionals are undefined. This establishes a source-level hazard, not proof that every prior NVIDIA frame visibly suffered from it.

The rest of the new cloud density/optical-volume implementation was implemented by the Codex team. The existing [Opus review](opus-final-review.md) concerns the earlier 0.2 architecture; it is not represented as a fresh Opus approval of the 0.3 volume model.

## Second scoped Sonnet patch: shallow refraction seed

A second no-tools Sonnet turn (actual `claude-sonnet-5-5`, 25.584 seconds, success) implemented `waterRefractionPath` and its caller. Above-water top surfaces now initialize the trace/fallback using local vertical depth divided by the downward Snell-ray component, instead of a grazing view-ray distance. Side faces and underwater views retain the old bounded path. Fresnel, extinction coefficients and trace foreground guards were not changed.

Codex rejected the generated caller's redundant depth declaration and invented `receiverHeight` variable, using the existing `verticalDepth` instead. This is a reviewed implementation contribution, not an unmodified AI patch or independent validation. The new real-GLSL GPU probe first failed on the missing helper, then passed after implementation: a one-metre shore gives about 1.51 metres of initial optical path rather than a 20-metre grazing distance; side/underwater distances and zero depth are preserved. This probe validates the helper, not the complete screen-space intersection or physical seabed reconstruction.

## Third scoped Sonnet patch: commit only converged refraction

A third successful no-tools turn (`claude-sonnet-5-5`, 19.743 seconds) changed production `refractionTrace` to commit a UV/path only after the depth iteration converges. Guard failures, offscreen projection and iteration exhaustion retain the original UV and Snell-depth fallback. Downward top-surface rays no longer accept a sky texel as a seabed hit. Underwater/side sky returns remain unchanged.

An actual GPU regression executes the extracted production tracer against a controlled depth texture. Before the fix, an offscreen second iterate returned a stale UV and 0.947753-metre path instead of its 0.3-metre initial path; afterward it preserves the fallback. A separate converged receiver still commits a one-metre ray-distance hit. This is a synthetic depth-texture regression, not a claim to reconstruct offscreen geometry. Codex reviewed/applied the patch and separately tested the game.
