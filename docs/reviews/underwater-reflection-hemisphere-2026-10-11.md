# Underwater reflection hemisphere candidate

The production water shader previously limited an optical normal by its
eye-facing cosine, but did not require its reflected direction to remain on
the eye side of the rasterized interface. An eye-facing shading normal alone
does not establish that constraint. A reflection crossing the geometric plane
is inconsistent with tracing that ray exclusively through the incident water.

The candidate in `waterReflectionNormal` leaves already-admitted normals
unchanged. For rejected normals it searches the normalized interpolation
toward the eye-oriented raster normal, retaining the admitted endpoint after
twelve bisections. The same corrected normal feeds Fresnel, refraction and
reflection. It applies only to underwater upper surfaces, not ordinary
above-water shading or true bottom faces.

This is a shading-normal consistency correction, not reconstructed wave
self-occlusion, missing model-owner coverage, a rough-interface transport
integral or proof that the visible polygonal rim originates from this condition.
In particular it does not invent reflection radiance for unknown receivers.

NVIDIA compile/link validation succeeded on RTX 3080 Ti / driver 580.173.02.
The existing production-main underwater backface GPU regression also completed
successfully, including same-top opposite windings, unknown top, true bottom,
thin-column and multiple-height controls. Raw artifacts are retained under
`reports/2026-10-11-display-water/underwater-reflection-normal-v78`.
The new dedicated `waterReflectionNormalProbe` directly executes the production
helper on a 17-by-17 optical-normal/view-angle grid. An independent double
precision angular oracle checks both unchanged normals and the admissible
reflection boundary, excluding non-eye-facing inputs and exactly tangential
boundaries. On the same NVIDIA context, 72 rejected directions were corrected
and 145 already-admitted normals were unchanged. The output must remain in
the incident hemisphere and agree with the angular boundary to 0.001 per
normal component (unchanged controls: 0.000001).

Command: `build/glcheck shaders --underwater-backface-only
reports/2026-10-11-display-water/underwater-reflection-normal-v79`, with the
NVIDIA EGL vendor selected. The command completed with exit zero, followed
by all retained backface controls. This direct helper test is not an actual
natural-scene branch-coverage observation, a critical-angle transmission
test, a three-dimensional exhaustive proof or temporal acceptance.
Actual natural underwater capture and moving-camera A/B remain required
before adoption; the ordinary installed pack has not been replaced.

## Natural runtime decision

The v80 A/B runtime is now complete. Four original scene PNGs were visually
inspected; folded/compressed sky-window edges and dark polygonal exterior
patches remain in both roles. The natural visual goal is not accepted.
Wave phases were not locked, and moving captures have different final yaw;
therefore these are not same-wave pixelwise causal comparisons, and differences
cannot be attributed solely to the correction.

The ordinary fragment shader invocation was removed after review. The helper
and dedicated GPU test remain available for research, with experimental v80
ZIPs and all runtime evidence preserved. The hemisphere invariant alone does
not solve the actual requested end state. Further work must separate optical
normal/critical-angle behavior from missing reflected receiver coverage,
rather than adopt this normal correction as a completed rim fix.
