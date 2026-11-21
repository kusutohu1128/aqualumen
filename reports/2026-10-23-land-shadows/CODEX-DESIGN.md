# Candidate B, texel-centered metric receiver-plane PCF

Parent-condensed record of the completed independent /root/land_shadow_design response. The full response was received and read in the team conversation. This is not a verbatim extra review.

## Problem and caller usage

Choose metric, texel-centered receiver-plane PCF using the existing comparison sampler. No raw-depth sampler or shared shadow-state change is permitted. This is antialiasing softness, not blocker-dependent PCSS or contact-hardening sunlight.

The two opaque wrappers replace their legacy lighting include with land_lighting.glsl. Their existing terrainLight calls stay unchanged. The adapter includes legacy shadows and the new land_shadows, aliases shadowVisibility to landShadowVisibility only while instantiating the unchanged lighting body, then immediately undefines it. Water, composite and receiver-source paths keep the old includes and function.

## Data shape

LandShadowReceiver contains lightPosition and lightNormal in metres, clipToLightXY mat2, projectionOffset vec2, depthProjection vec3, depthOffset, depthPerMetre, filterRadius and valid status. Constructor validates finite orthographic projection, XY independent of Z, nonsingular XY matrix and a non-grazing normal. Unsupported legitimate finite projection/normal cases use legacy visibility.

Public landShadowVisibility(relativePosition,normal) hides the projection/refusal/filter details. Internals makeLandShadowReceiver and landShadowTap construct a valid receiver and convert a metric offset to the actual texel centre and plane reference depth. Callers do not coordinate stages.

## Geometry

For undistorted clipXY u, r=length(u), d=.15+.85r, mapped UV is F(u)=.5*u/d+.5. Its Jacobian is .5*(I/d-.85*outerProduct(u,u)/(r*d*d)); the origin uses I/.3. Combine with shadowProjection XY to compute UV per light-space metre.

Use the existing deterministic golden-angle pattern and SHADOW_SAMPLES. Initial metric radius is35mm, expanded only to represent approximately one local shadow texel. This is explicit antialiasing softness, not the Sun's physical penumbra. Far radial texels still limit quality.

Each metric tap is projected through unchanged distortion and snapped to (floor(uv*resolution)+.5)/resolution. Invert distortion at that actual centre. For v=2uv-1, u=.15*v/(1-.85*length(v)). Refuse invalid denominators. Invert projection XY to get sampled light-space XY, then evaluate plane dz=-(nx*dx+ny*dy)/nz. Project Z with the unchanged .2compression and .5window-depth mapping. Reference is evaluated at the sampled texel, not merely the original tap, so hidden hardware bilinear comparison support no longer mixes four distinct planes under one reference.

Proposed residual bias is2mm of light-space depth plus a small D24/D32F-qualified numerical floor. It is a test hypothesis. Do not increase it to conceal caster interpolation errors.

## Critical caster gate

The unchanged shadow vertex program warps only vertices; rasterization interpolates depth linearly over warped triangles. An inverse-distorted physical plane is not generally identical to that coarse raster plane. The first native gate must render actual shadow.vsh/fsh with1m and larger sloped faces, including origin-crossing and off-axis cases, and report warp residual separately.

If ordinary1m geometry cannot meet predeclared acne/contact bounds, do not accept a larger hidden bias. Preserve ordinary0.6 and report caster deformation/tessellation as a separate architectural issue. This limitation was added in response to the parent's explicit coarse-caster question, not discovered by running a GPU test.

## Coverage and invariants

Bounds-check every sample before texture access. Invalid taps represent unshadowed coverage and are never clamped onto an edge. Preserve115.2to144m horizontal fade. No depth/MRT writes, new sampler resources, stochastic per-frame rotation, caster, resolution or global directive changes. Existing Sun/Moon attribution, AO, rain, exposure and cutout alpha rule stay unchanged.

Finite degenerate projection and grazing normals use the documented legacy fallback. Nonfinite-input handling still needs an explicit outcome because the legacy function itself cannot promise finite output for invalid inputs. Parent must reconcile that boundary before implementation.

Preserved water algorithm bytes do not imply identical water images. Opaque C0/C5 changes naturally affect downstream C4/C8, reflections and caustic inputs.

## Alternatives

Raw-depth PCSS provides genuine contact-hardening with penumbra radius tan(.00465)*blocker-receiver separation. It loses because raw shadowtex1 and per-texture filtering introduce unresolved pinned-Iris state assumptions, and global separate hardware samplers can reinterpret water/composite samplers. A compare-sampler depth search is costly and still inherits coarse caster error.

A copied land-lighting body loses because it duplicates irradiance and Sun-attribution ownership. A single guarded scoped alias is smaller and can be tested against exact nonopaque expansions.

## Native and archive verification

Use real generated shader libraries and actual unchanged caster programs in an owned NVIDIA compatibility context. Test actual1m sloped casters first, old contact leaks, warp residual at centre/edge, world-space transition widths, injected analytic plane plus unsnapped negative control, Sun/Moon orientations, cutout, bounds, refusal and finite values. No native result is actual Minecraft appearance evidence.

The archive keeps all45ordinary shader entries. Only two wrapper payloads differ; new libraries are added. Check nonopaque preprocessed expansion equality, alias nonleakage and compile/link of every original program pair. No active game or config mutation is needed.
