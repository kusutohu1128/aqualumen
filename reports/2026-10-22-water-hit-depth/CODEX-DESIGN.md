# Codex independent design

Source is the completed `/root/depth_how_architect` return. This is the parent's condensed record, not an additional independent review.

Recommend accepted continuous hits project into `gl_FragDepth`. Composite retains the single eye-to-surface Beer operation reconstructed from `depthtex0`. An optical-distance MRT alone fixes attenuation but leaves raster visibility inconsistent, requiring opaque-color restoration and later-translucency ownership to fix it.

Initialize `gl_FragDepth=gl_FragCoord.z` before every nonwater early exit. Do not request early fragment tests. Accepted points must be finite with positive clip W, in-range projected depth, and the same screen pixel. Projection rejection retains the complete raster fallback. Do not clamp depth toward an opaque occluder.

Two occlusion directions must work. If raster water is nearer than an opaque plane but the solved point is farther, opaque wins. If raster water is farther but the solved point is nearer, water wins. Choose an opaque depth strictly between old and new depths and assert the surviving color and depth. A policy that merely preserves raster visibility is not equivalent to continuous primary visibility.

Move optical view point, initial straight path, shadow point and interface surface Y together. Preserve raster derivatives, normals and eligibility. Composite scatter illumination remains eye-local. Caustic/source receiver approximations, shoreline and later interface visibility remain outside this bounded unit. The original recommendation also moves reflected-source incident surface Y, which the parent will assess separately from source-radiance approximation.

C2 can be composite's actual distance/transmission output, with an explicit new schema. Keep separate strict depth-format validation and RGBA32F color validation. Capture actual depthtex0/1 and keep bindings stable before/after FINAL. A native compile is not actual Iris attachment proof.

Native checks must fail on hit1 and exercise both opaque straddles and unobstructed Beer. Actual near/deep checks must compare the same FINAL point, emitted depth, stored depth and composite distance/transmission. Add a fully blocking ceiling and a Lab occluder if the actual scene can straddle the interval. Otherwise actual straddle remains open.

The solve remains fixed-phase, zero-ripple, known-deep-water and limited-footprint TEST. It cannot create coverage outside the coarse mesh. R2, general translucency, complete physical accuracy, performance and visual completion remain open.
