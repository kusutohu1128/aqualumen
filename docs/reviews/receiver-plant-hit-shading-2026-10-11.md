# Plant hit material and shading checkpoint

The plant geometry publisher now optionally publishes a fourth RGBA32F texture
in the same transaction. Each geometry primitive owns one six-texel material
row containing its three vertices' UV, block/sky light, tint and AO. Exact packet
identity and world/frame/resource epoch are required. Allocation failure or
epoch drift leaves the publication unavailable rather than exposing partial
geometry/material state. The legacy three-texture path remains available.

`water_plant_material.glsl` reconstructs attributes from barycentric weights or
the corresponding ray hit. Ray reconstruction checks primitive extent, unit
direction, travel and UV correspondence. It does not interpolate shaded RGB
from alpha-covered endpoints into an arbitrary leaf hit.

`water_plant_shading.glsl` uses the existing `shadeOpaqueReceiver` lighting,
the actual interpolated material, the triangle's ray-facing geometric normal,
camera-relative position and an explicit atlas LOD. It requires atlas ownership,
alpha-qualified geometry and a cutout-covered texel. Total and direct-Sun RGB
are paired, finite, nonnegative and direct-Sun bounded by total RGB.

Evidence is from controlled RTX 3080 Ti GPU fixtures: exact material upload and
readback, vertex/interior interpolation, ray-hit correspondence and independent
tinted/block-light shading expectations. Existing intersection, publication and
source-shading regressions remain separate tests. This is not Minecraft visual
acceptance or proof of complete live model ownership. The helper is not yet
connected to the ordinary water-reflection path. Live coverage, atomic draw
binding integration into the live shader, Sun-positive plant controls, temporal views
and usable actual Minecraft performance remain open.

The controlled Java GPU draw binding now recognizes an active material sampler,
requires its paired publication, rejects unit aliases and restores the caller's
texture/sampler state. Geometry-only programs retain their original binding
contract. These fixture checks do not prove a live water shader uses that path.

The receiver DDA has an opt-in `AQUALUMEN_PLANT_SHADED_RECEIVER` callback into
that shading helper. Without the macro, known leaves still stop with unavailable
radiance. With it, only an admitted first leaf can supply its own material color;
the prior water/complete-owner/first-object gates remain authoritative. Ordinary
shader packs do not enable either plant macro at this checkpoint.
