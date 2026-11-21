# Actual 0.8.3 visual audit — goal not accepted

Root viewed all six original 1600x900 Minecraft PNGs from
`captures/v083-radiance-smoke-20261002-1610`. The exact candidate runs without
Iris fallback. These are stills with real camera/head metadata, not native
fixtures or a motion-quality test.

- Coast: broad cyan/mint shallows, long pointed dark bands and visibly sharp
  transitions remain. Bottom textures are visible, but this is not accepted
  as natural shore transport.
- River: the same saturated shallow areas and irregular dark/surface-reflection
  boundaries remain. Screen-space reflection of trees is visibly distorted.
- Ocean: the deep surface is darker and comparatively coherent, but repetitive
  cloud structure and the horizon appearance remain artificial.
- Underwater up near/deep/tilt: no old inner quadrilateral or duplicate sky map
  is visible in these three images. A strong round sky window, wrinkled rim and
  nearly uniform dark exterior remain. Deep also contains ordinary water
  particles. Natural underwater appearance is not accepted.

Near/tilt measured head depth is 0.499889308m; deep is 3.249889308m.
All are first-person, actual camera and local eye match, submerged WATER,
same fixed daytime 6000 and no terrain placement. The underwater path itself
is unchanged by the above-water direct-C8 radiance correction. Sequential
stills have different animation phases; they are not a fixed-phase visual A/B
or evidence that the shallow cyan problem improved.

## Next discriminating test

A round window alone is not sufficient evidence of a bug. Snell's law with
water/air indices 1.333/1 gives a flat-surface critical half-angle about48.61deg;
the actual projection must be included when comparing pixel radii.
This is a model inference from the
[PBRT reflection/transmission model](https://www.pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission),
not proof that the current full image is physically correct.

Before changing the index or cosmetically shrinking the window, compare dense
direction markers through original water VS/FS main against independently
projected flat-surface Snell/TIR positions. Existing sparse tests do not prove
this angular map over the whole image. Then distinguish these ranked candidates:

1. The broad round shape is expected Snell/projection behaviour; flat direction
   markers should match the independently computed angular map.
2. Extra rim warping follows fine optical normals versus coarse rendered
   geometry/known-column transitions; a qualified wave case should isolate
   deviations after the flat map passes.
3. A dark sphere-like exterior comes from an offscreen reflection miss falling
   back to scattering alone; independent visible reflection tags must separate
   that missing information from a wrong refraction direction.

Opaque/sky/miss classification boundaries remain another possible local seam,
not a confirmed cause. Do not call the underwater issue fully solved from the
absence of the older rectangular artifact.

Remaining full-goal work includes shore continuity/color, cloud morphology,
moving views/contact wakes, day/weather/dimension compatibility and broader
optical calibration. This packet does not close any of those requirements.
