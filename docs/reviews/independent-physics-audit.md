# Independent physics and pipeline audit

Date: 2026-10-01. Baseline inspected: `b14e34c8dc164634d012cb5e15cce2ff178562f7` (Aqualumen 0.1.0). This records review findings before the subsequent implementation; a finding is not proof that the final release still contains it.

## Highest-priority corrections

1. **Transparent blending:** `gbuffers_water.fsh:43-48` handles glass and other translucent terrain by mixing the immutable opaque `colortex4` snapshot and writing alpha 1. `shaders.properties:14` disables blending for the entire pass. Every successive layer consequently replaces earlier transparent layers. Restore ordinary source-alpha blending, return lit RGB plus texture alpha for nonwater materials, and keep water's already-composited result at alpha 1. Preserve `colortex4` as the water refraction/SSR input; do not read the actively written `colortex0` in gbuffers.
2. **Atmospheric quadrature:** `atmosphere.glsl:21-25` uniformly samples a 100 km atmosphere with six midpoint samples. The first vertical sample is at 8.33 km, missing almost the entire 1.2 km Mie density layer. Use nonuniform intervals concentrated near the observer with their correct interval lengths; 12-16 segments are a reasonable starting point. Compute solar transmission once in the sky pass rather than repeating the integration in all lit fragments.
3. **Sunlight leaks outside shadow coverage:** `lighting.glsl:7-8` gates direct light with the shadow map but not the sky-light value. `shadowVisibility` returns fully visible outside its coverage. The resulting distant or unmapped interiors can receive sun. Gate direct illumination conservatively by sky exposure as well as the shadow map. Skylight is a heuristic occlusion signal, not a replacement for directional shadowing.
4. **Glint stability:** `water.glsl:18-25` uses a narrow point-light GGX lobe at roughness 0.10, while the normals contain short waves. Apply screen-space normal variance to the effective microfacet roughness; include a finite angular sun-size floor. Validate moving-camera glints using video or consecutive frames, because screenshots cannot establish temporal stability.
5. **Wave dispersion:** `waves.glsl:12` multiplies the dispersion-derived angular frequency by `WIND_SPEED`. The stated `omega^2 = g*k` therefore holds only at wind speed 1. Use wind to tune amplitudes and/or wave-spectrum wavelengths while computing each frequency from its actual wave number; normalize direction vectors if they are intended as unit headings.

## Numerical evidence for atmospheric error

The table compares the baseline six-sample method against a 12,000-segment double-precision midpoint reference using exactly the source's planet radius, density scale heights and altitude 2 m. The column is an integral of relative Mie density over path length, in meters; it is not measured weather data.

| Sun elevation | Baseline Mie column | Reference Mie column | Relative error | Baseline blue transmission | Reference blue transmission |
|---|---:|---:|---:|---:|---:|
| 90 degrees | 16.04 | 1198.00 | -98.66% | 0.80038 | 0.74646 |
| 45 degrees | 23.63 | 1693.91 | -98.60% | 0.72962 | 0.66163 |
| 15 degrees | 99.66 | 4616.65 | -97.84% | 0.41943 | 0.32874 |
| 5 degrees | 1305.43 | 13429.25 | -90.28% | 0.08118 | 0.05008 |
| 1 degree | 30535.29 | 49962.45 | -38.88% | 0.00075 | 0.00044 |

## Companion Mod and local GPU solver constraints

The proposed companion Mod is appropriate for passing real player/boat water contacts into a local persistent interaction field. A linear height-field wave equation is a useful, bounded first release. It should be described as that model, not a complete nonlinear shallow-water or block-volume fluid solver.

- A centered explicit 2D wave discretization requires `c*dt/dx <= 1/sqrt(2)` for equal x/z spacing, where `c=sqrt(g*h)` for an assumed shallow effective depth. Leave margin below the limit. Bound elapsed time after pauses and use fixed or semi-fixed substeps so wave speed does not depend on render FPS.
- Use exponential damping per elapsed second and time-scaled source forcing. A source added once every frame with constant amplitude produces very different wakes at 60 and 500 FPS.
- Ping-pong state buffers are required: a dispatch must never overwrite values that neighboring invocations still need to read. Initialize every state element on setup/reload; do not rely on unspecified initial SSBO contents.
- Keep compute passes serial. Integer-cell recentering should copy overlap consistently or reset visibly bounded state on teleport; handle newly exposed cells. Water-plane height must gate interaction sampling so contacts do not affect vertically separated pools.
- Without a terrain/water mask, the solver has no true shoreline boundaries. State this limitation. A contact-only water-height uniform is insufficient to establish volume-conserving flow or realistic wave breaking.
- Existing GLSL 330 water programs need GLSL 430 compatibility or the relevant ARB extension before reading SSBOs. Add all compute passes to the compilation harness and test actual dispatch/state evolution.
- Graceful behavior without the companion Mod is necessary: missing custom uniforms should leave the analytical water active and disable contact forcing, rather than sample uninitialized positions.

## Iris integration verified against installed 1.8.8

The installed `iris-fabric-1.8.8+mc1.21.1.jar` was inspected read-only with `javap -c -p`.

- `net.irisshaders.iris.gl.program.ComputeProgram.dispatch` issues `IrisRenderSystem.memoryBarrier(8232)` before serial dispatch.
- `net.irisshaders.iris.pipeline.CompositeRenderer` issues `memoryBarrier(8232)` after a compute group.
- Decimal 8232 contains `GL_SHADER_STORAGE_BARRIER_BIT` (8192), `GL_SHADER_IMAGE_ACCESS_BARRIER_BIT` (32), and `GL_TEXTURE_FETCH_BARRIER_BIT` (8).

Thus serial SSBO communication is supported by the inspected pinned Iris runtime. The current ordering documentation retains an obsolete note claiming no released SSBO support and must not supersede the actual runtime evidence.

Primary API references consulted: [Iris program ordering](https://shaders.properties/current/reference/programs/overview/), [gbuffers transparency](https://shaders.properties/current/reference/programs/gbuffers/), [colortex constraints](https://shaders.properties/current/reference/buffers/colortex/), [SSBO declarations](https://shaders.properties/current/reference/buffers/ssbo/), [compute ordering](https://shaders.properties/current/reference/shadersproperties/ordering/).

## Acceptance and claim limits

The existing render-loop intervals include the main client render path rather than a GPU timer query. The artificial warmed-up coast is useful regression evidence but cannot establish a 60 FPS floor for normal exploration, chunk generation, complex builds, rain, boats, caves or other dimensions. Record actual framebuffer size, shader-pack identity, GPU renderer and companion activation in the next benchmark. Include a natural world, water interaction and moving viewpoint. Collect worst-frame and frame-budget-exceed counts alongside averages and 1% lows.

The baseline lower sky hemisphere clamps to the horizon (`atmosphere.glsl:38-39`), sunlight disk and GGX strengths have independently chosen exposure factors, SSR cannot see offscreen geometry, and caustics multiply a horizontal-receiver approximation into already lit background colors. These can be acceptable first-release limitations if stated accurately and visually checked. They are not a basis for claiming full radiometric calibration, global illumination, path-traced reflection, water-volume physics, or complete fluid simulation.
