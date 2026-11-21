# Land shadow subsystem

Read-only how explanation from /root/land_shadow_how, retained by the parent. No game, GPU, config or world operations were performed by the explorer.

## Overview

Aqualumen uses one distorted shadow map for terrain, water, Moon illumination and aerial scattering. Current receiver filtering is fixed-radius PCF. It has no blocker-dependent penumbra. The installed ordinary0.6 archive differs from the dirty root, so a land preview must start from the frozen ordinary ZIP.

## Key concepts

shadowtex0 is a sampler2DShadow. The actual Iris texture/sampler state determines comparison filtering. distortShadow magnifies central XY coverage and compresses clip Z by0.2. shadowVisibility accepts camera-relative position and normal and returns visibility, fading toward unshadowed near144m. terrainLight keeps Sun radiance separate from ambient, Moon and block light and writes opaque C0 and direct Sun C5.

## How it works

The unchanged shadow vertex program applies the shared distortion after ftransform. Its fragment program discards texture-alpha times vertex-alpha below0.1. The properties enable entity and block-entity shadows and disable translucent shadows.

The receiver normal offset is0.015+distance*0.00025metres. Projection uses shadowProjection*shadowModelView, the same distortion, and guarded map bounds. Filtering averages a deterministic golden-angle disk with1.6texel radius and subtracts depth bias0.00015. Horizontal coverage fades between115.2and144m.

The two opaque wrappers include shared lighting and terrain bodies. terrainLight multiplies direct irradiance by orientation, visibility, sky access and rain, and uses the same visibility function for the Moon. Ordinary0.6 terrain calls terrainLight directly. Root terrain uses shadeOpaqueReceiver instead.

Water direct lighting, foam and its nonwater-material fallback use the legacy shared path. Underwater composite samples it for in-scattering. Aerial sun visibility separately samples shadowtex0 and denies direct light on unknown coverage. Root-only receiver_source is a fragment-draw path through ReceiverSourceDraw, not compute. Water-plant receiver shading also calls the shared opaque receiver helper.

```text
shadow.vsh + alpha-tested shadow.fsh
                  |
            shadowtex0
                  |
        legacy shadowVisibility
           /              \
    terrainLight      water/composite
           |
      C0 total + C5 Sun
           |
     deferred C4/C8 snapshots
           |
   water/reflection/caustic inputs
```

## Where things live

- shaders/shadow.vsh and shadow.fsh own shared caster geometry and alpha rejection.
- shaders/lib/shadows.glsl owns shared projection, offset, filter and coverage.
- shaders/gbuffers_terrain.fsh and gbuffers_textured_lit.fsh are narrow land opt-in points.
- shaders/lib/lighting.glsl owns shared irradiance and Sun attribution.
- shaders/deferred.fsh publishes opaque C4/C8 snapshots used by water.
- shaders/lib/aerial.glsl samples the same shadow map for aerial scattering.

## Gotchas

All45ordinary shader entries exist in root, but9differ. They are water FS/VS, atmosphere, clouds, lighting, terrain FS body, water, waves and shaders.properties. The caster, shared shadows, terrain VS, opaque wrappers, composite, aerial and settings are byte-identical. Root receiver and plant libraries are absent from ordinary.

A new land-shadow library selected only in the two opaque wrappers can preserve shared lighting/shadows, caster and water programs. A scoped compile-time alias around the lighting include is a narrow candidate boundary; a new land-lighting module is an alternative. Global sampler/map settings must not silently reinterpret legacy programs.

Preserved water algorithms do not imply identical water final images. Opaque C0/C5 changes reach deferred C4/C8 and therefore reflections, refraction and caustic source illumination. Static fixed-radius code proves only the absence of contact-dependent softness. Acne, floating contacts, distortion artifacts and sampler binding problems are hypotheses until tested.
