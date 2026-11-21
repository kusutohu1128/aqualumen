I couldn't read the architect `SKILL.md` or `runner-prompt.md`: the sandbox only lets file tools read inside the repo. So I followed the caller-first shape your brief describes, not the skill's exact template. I wrote no plan file and changed nothing. I made 14 file reads (2 of them the denied skill files) plus 2 searches.

# Land-shadow candidate: receiver-plane PCF on the existing compare sampler (`shadowtex0`)

## Overview, flow and gotchas

The flow stays the same as ordinary0.6: the shadow pass writes `shadowtex0`, then `terrainLight` uses it to produce opaque C0 (total light) and C5 (direct Sun). The only changed step is the one that turns the shadow map into a visibility value, and only for the two opaque wrappers. The candidate keeps the legacy projection, normal offset, golden-angle disk, tap count, footprint, coverage check and edge fade exactly. It changes **where each tap's comparison depth sits**:

- **Now:** a flat `coord.z−0.00015`.
- **Candidate:** the receiver's own plane, with an analytic gradient in shadow-map coordinates, minus a small bias in metres.

That targets two failure modes: acne on slopes and at low Sun, and light leaking at contacts (peter-panning).

**Gotchas grounded in the pinned source:**

- **Radial distortion is strongly anisotropic.** With `d=0.15+0.85r`, the distortion's stretch factors are 1/d along the circle and 0.15/d² along the radius. Assuming `P00=1/144` at 2048 px, one map texel covers about 0.021 m at the player. At r=0.5 (72 m) it is 0.31 m radially by 0.08 m tangentially; at the map edge, 0.94 by 0.14 m. The fixed 1.6-texel disk therefore spans about 0.5 m radially at 72 m. A flat bias cannot cover a slope that varies across that span: a 30° Sun gives about 1.73×0.5 ≈ 0.86 m of receiver depth change against a 0.19 m bias. That predicts acne on distant slopes, which is a hypothesis until F1 below tests it.
- **Depth units.** `c.z = 0.1·(P22·q.z+P32)+0.5`, so one metre is `0.1·|P22|` in map depth. If far−near is 256, the legacy 0.00015 bias equals about **0.19 m**. That is the likely source of detached contact shadows at sunrise and sunset. The candidate reads P22 at runtime, so the 256 m figure is never assumed in code.
- `shadowTranslucent=false`, so water never casts. Cutout casters keep their holes because `shadow.fsh` is unchanged.
- **Caster linearisation error.** The shadow pass distorts per vertex, so 1 m faces are rasterised linearly in distorted space. Near the centre the curvature error is roughly `37.8·(1/144)²/4` in normalised device coordinates, about **0.01 m**. The constant bias covers it.

## Caller usage and module map

Each opaque wrapper changes one line, and both wrappers stay identical to each other (they share a pinned hash):

```glsl
#include "/lib/shadows.glsl"        // unchanged: shadowtex0, distortShadow, consts
#include "/lib/land_lighting.glsl"  // was "/lib/lighting.glsl"
#include "/lib/terrain.fsh.glsl"    // unchanged, still calls terrainLight(...)
```

| Entry | Status |
|---|---|
| `lib/land_shadows.glsl` | new, about 60 lines: frame and visibility |
| `lib/land_lighting.glsl` | new, about 10 lines: scoped instantiation of the legacy lighting |
| `gbuffers_terrain.fsh`, `gbuffers_textured_lit.fsh` | one-line include swap |
| Everything else, including `shaders.properties`, `shadow.*`, `shadows.glsl`, `lighting.glsl`, `aerial.glsl`, water, `composite` | byte-identical |

No new uniforms, samplers or `const` directives, so Iris's global shadow state cannot change.

## Core data shape and function sketches

```glsl
#ifndef AQUALUMEN_LAND_SHADOWS
#define AQUALUMEN_LAND_SHADOWS
#ifndef AQUALUMEN_SHADOWS
#error "land_shadows reuses legacy distortShadow/shadowtex0"
#endif
const float LAND_SHADOW_BIAS_M = 0.03;   // depth quantisation + caster linearisation (~0.01 m)
const float LAND_SHADOW_MAX_SLOPE = 4.0; // ~76 deg receiver plane cap
struct LandShadowFrame {
    vec3 coord;      // legacy-identical distorted map coord of offset receiver
    vec2 depthGrad;  // d(coord.z)/d(coord.xy) of the receiver plane
    float bias;      // coord.z units, >0 toward light
};
mat2 distortInverseJacobian(vec2 p) {
    float r=length(p), d=0.15+0.85*r;
    vec2 e=r>1e-6?p/r:vec2(1.0,0.0);
    return d*mat2(1.0)+(d*d/0.15-d)*outerProduct(e,e);
}
LandShadowFrame landShadowFrame(vec3 pos, vec3 normal) {
    vec3 offset=normal*(0.015+length(pos)*0.00025);               // legacy offset
    vec4 clip=shadowProjection*shadowModelView*vec4(pos+offset,1.0);
    vec3 ndc=clip.xyz/clip.w;
    LandShadowFrame f;
    f.coord=distortShadow(ndc)*0.5+0.5;
    vec3 nL=mat3(shadowModelView)*normal;
    vec2 g=nL.z>0.05?-nL.xy/nL.z:vec2(0.0);                       // dq.z/dq.xy, metres/metre
    g*=min(1.0,LAND_SHADOW_MAX_SLOPE/max(length(g),1e-6));
    vec2 pScale=vec2(shadowProjection[0][0],shadowProjection[1][1]);
    f.depthGrad=0.2*shadowProjection[2][2]*(distortInverseJacobian(ndc.xy)*(g/pScale));
    f.bias=0.1*abs(shadowProjection[2][2])*LAND_SHADOW_BIAS_M
          +length(f.depthGrad)/float(shadowMapResolution);           // one-texel bilinear reach
    return f;
}
float landShadowVisibility(vec3 pos, vec3 normal) {
    LandShadowFrame f=landShadowFrame(pos,normal);
    if (any(lessThan(f.coord,vec3(0.002)))||any(greaterThan(f.coord,vec3(0.998)))) return 1.0;
    float v=0.0;
    for (int i=0;i<SHADOW_SAMPLES;++i) {
        float a=float(i)*2.39996323;
        vec2 o=vec2(cos(a),sin(a))*sqrt((float(i)+0.5)/float(SHADOW_SAMPLES))*1.6/float(shadowMapResolution);
        v+=texture(shadowtex0,vec3(f.coord.xy+o,f.coord.z+dot(f.depthGrad,o)-f.bias));
    }
    float edge=smoothstep(shadowDistance*0.8,shadowDistance,length(pos.xz));
    return mix(v/float(SHADOW_SAMPLES),1.0,edge);
}
#endif
```

```glsl
// lib/land_lighting.glsl — instantiate legacy terrainLight with land visibility only here
#ifdef AQUALUMEN_LIGHTING
#error "legacy lighting already instantiated before land adapter"
#endif
#ifdef shadowVisibility
#error "shadowVisibility alias collision"
#endif
#include "/lib/land_shadows.glsl"
#define shadowVisibility landShadowVisibility
#include "/lib/lighting.glsl"
#undef shadowVisibility
```

## How the maths fits together

- **Map coordinates.** `coord.xy = 0.5·J·diag(P)·dq`, so `dq = 2·diag(P)⁻¹·J⁻¹·dcoord`. The receiver plane gives `dc.z = 0.1·P22·gᵀ·dq`. Because J⁻¹ is symmetric, the depth gradient per map coordinate is `Gc = 0.2·P22·J⁻¹·(g/diag(P))`.
- **Inverse distortion.** J⁻¹ is d along the circle and d²/0.15 along the radius. The slope therefore lives in the same space as the taps, and each tap costs one extra dot product.
- **Bias.** The bias term `|Gc|/res` is isotropic in map coordinates because anisotropy is already folded into Gc. It covers bilinear compare neighbours up to one texel from the tap.
- **Signs.** Every term keeps the sign of P22, so the code never assumes it.
- **Normal offset.** It stays at the legacy value, at most 0.033 m within 72 m, so it adds almost no peter-panning.
- **Predicted contact bias near the player at a 30° Sun:** 0.03 + 1.73×0.021 ≈ **0.066 m**, versus the legacy 0.19 m. This is analytical and assumes far−near=256.
- **Grazing receivers.** Where N·L is near zero (cross plants), the slope is clamped or set to zero. That degrades to a constant bias and is multiplied by about zero lighting anyway.
- **Day, Moon, night.** One shadow map follows `shadowLightPosition`, so the frame follows the Moon at night. Both `terrainLight` calls get the same value, exactly as in the legacy code.
- **Sampling stability.** The same deterministic disk, with no screen noise. There is no temporal accumulation, so randomising the rotation would only add flicker.

## Invariants

1. Only the two wrapper payloads change, by exactly one line each. The only new entries are `land_shadows.glsl` and `land_lighting.glsl`.
2. Legacy `shadowVisibility`, `shadow.*`, `shadowtex0` and Iris state are untouched. No `shadowtex1` and no `separateHardwareSamplers`.
3. Fetch count is `SHADOW_SAMPLES`, as before. Coverage test, edge fade and disk are identical to legacy, so where there are no casters the result is identical.
4. The output is always in [0,1] and never NaN, including the zero-slope fallback.
5. Water algorithms are untouched. Opaque C0/C5 changes still reach the C4/C8 snapshots, so there is **no claim that water images stay identical**.

## Selected shape versus the rejected alternative

**Rejected: PCSS (blocker search with contact hardening) on raw depth.**
- **Physical benefit is small.** Sun penumbra width is `2h·0.00465`, about 0.0093·h. It reaches the legacy kernel diameter (about 0.068 m near the player) only when the blocker is about 7 m above the receiver. Most Minecraft blockers would therefore look unchanged unless the penumbra were exaggerated, which is not physical. A 64 m blocker needs a search radius of about 28 texels, which is costly.
- **Unresolved resource state.** It needs `shadowtex1` sampled as plain `sampler2D` with compare mode off. That leaves open:
  - the per-texture filtering directive spelling in pinned Iris 1.8.8;
  - whether `shadowtex1` is filled when `shadowTranslucent=false`;
  - whether the directive is truly per-texture rather than reinterpreting `shadowtex0` for water, composite and aerial.

  None of these is proven.
- **A compare-sampler variant** (blocker-distance histogram from `shadowtex0` at a few reference offsets) multiplies fetches by K and only gives coarse, bucketed blocker distances.

**Selected:** this candidate fixes geometric bias errors that apply everywhere, adds no new global state, and is a small change. The same `LandShadowFrame` is what PCSS would need later, so it is not throwaway work.

**Boundary assessment.** The alias is not hidden: it sits in one named adapter, and the wrappers show it explicitly. It is fragile in three places, each handled:
- **Include-guard order** → turned into an `#error`.
- **A different-arity call** → a compile error.
- **Iris preprocessing** expanding the macro before transformation → an open question for root to check against the decompiled pinned Iris.

A copied `landTerrainLight` was rejected because it would silently drift from the C5 Sun-attribution rule. The cleaner long-term shape, for later root integration rather than this preview, is `terrainLight(..., float sunVisibility)` in shared lighting.

## Minimum deterministic native tests (owned EGL context, real archive entries)

These would extend `tools/glcheck.cpp`, expanding includes from the preview ZIP. Casters are drawn with the real `shadow.vsh` and `shadow.fsh` into a depth texture with compare mode and linear filtering. Receivers are evaluated by a test fragment shader that includes the real `shadows.glsl` and `land_shadows.glsl`. Projections are Iris-like (±144 m; far−near ∈ {256, 512}, labelled an assumption).

**Fail-first:** run with `landShadowVisibility` aliased to legacy, and F1/F2 must fail.

| Test | Setup | Pass condition |
|---|---|---|
| F1 Slope acne | Sun 12°, sun-facing slope at r ∈ {0.5, 0.8} | Land = 1 at every grid point; record legacy's minimum |
| F2 Contact leak | 1 m cube, Sun 30°, ground point 0.10 m past the base, r < 0.1 | Land ≤ 0.05; record legacy. If legacy doesn't leak there, the 0.19 m analysis is wrong and the candidate's benefit must be re-argued |
| F3 Parity | Deep umbra, open ground, edge-fade band with no casters | Land == legacy |
| F4 Self-shadowing | Caster tops at r ∈ {0, 0.5, 0.95}, Sun {90, 45, 15}°, Moon as shadow light | Lit |
| F5 Cutout | Checkered-alpha leaf caster | Mean visibility 0.3–0.7 |
| F6 Off-map / z range | Receivers outside the map | Exactly 1, same as legacy |
| F7 Grazing | N·L = 0.01 | Finite, in [0,1] |
| F8 Determinism | Rerun; different fragment coordinates | Bitwise equal |

**Compile check:** all 45 programs plus the two new libraries compile and link; record `GL_RENDERER`.

**Archive tests:**
- The base is `ordinary-0.6.zip` after SHA `6ceb9cf…` is verified.
- Every non-wrapper entry's sha256 equals the extracted ordinary entry.
- Each wrapper diff is exactly the one include line.
- The entry set is ordinary plus the 2 new libraries.
- `grep` finds no `shadowtex1`, `HardwareFiltering` or `separateHardwareSamplers` in new entries.
- The expanded non-opaque programs are byte-equal to ordinary.

## Implementation-sized contract

- **Scope:** about 70 new lines in 2 libraries, plus 1 line in each wrapper.
- **Packaging:** a preview-only build reads the pinned ordinary ZIP and never the root `shaders/`. It produces a separately named ZIP, installed into Aqualumen Lab without becoming the active pack.
- **Out of scope:** settings, properties, caster, sampler or water edits.
- **Cost:** no speed claims. Fetch count is unchanged; per-fragment math grows by roughly 30 ALU operations plus one dot product per tap. Harness timings would be labelled as harness timings.

## Where coverage degrades and where the evidence ends

**Still degraded:**
- Fade from 115 m outward.
- Casters outside the ±144 m light-space map, such as long low-Sun mountain shadows.
- Far radial texels of 0.3–0.94 m: the slope bias grows with them, so distant contacts still leak, though no worse than now.
- Smooth entity normals only approximate a plane.
- No contact hardening.

**Not verified by me:**
- Pinned Iris near/far planes, `shadowModelView` orthonormality, depth format, square projection (`P00==P11`).
- Whether the macro alias survives Iris preprocessing.
- In-game appearance.

All numbers above are analytical from the pinned constants.
