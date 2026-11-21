# Source comparison, not imported code

Checked 2026-10-22 against the publisher's repository. Crest revision db0658ff0b2e93e4a9e28cc2867509658b0ecc00 is [MIT licensed](https://github.com/wave-harmonic/crest/blob/db0658ff0b2e93e4a9e28cc2867509658b0ecc00/LICENSE). No Crest or other shader-pack source was copied into Aqualumen.

[OceanReflection.hlsl](https://github.com/wave-harmonic/crest/blob/db0658ff0b2e93e4a9e28cc2867509658b0ecc00/crest/Assets/Crest/Crest/Shaders/OceanReflection.hlsl) separates underwater incoming light from reflected underwater scatter and derives the relevant incidence angle. It uses a Schlick-based configurable approximation. It is not evidence that arbitrary displaced-interface visibility is solved. Retain Aqualumen's exact dielectric Fresnel/TIR rather than replacing it with an artistic coefficient.

[OceanEmission.hlsl](https://github.com/wave-harmonic/crest/blob/db0658ff0b2e93e4a9e28cc2867509658b0ecc00/crest/Assets/Crest/Crest/Shaders/OceanEmission.hlsl) uses a screen-space normal-derived refraction offset with depth checks that reject foreground samples. That is a practical screen-space approximation, not a reference solution for Aqualumen's directional refracted sky. Copying its offset would not diagnose the current folded Snell mapping.

[OceanNormalMapping.hlsl](https://github.com/wave-harmonic/crest/blob/db0658ff0b2e93e4a9e28cc2867509658b0ecc00/crest/Assets/Crest/Crest/Shaders/OceanNormalMapping.hlsl) relates normal-map scale to geometry scale and blends between levels for continuity. This motivates checking Aqualumen's geometry/optical bandwidth relationship but does not prove that relationship caused the observed broad rim.

[UnderwaterEffectShared.hlsl](https://github.com/wave-harmonic/crest/blob/db0658ff0b2e93e4a9e28cc2867509658b0ecc00/crest/Assets/Crest/Crest/Shaders/Underwater/UnderwaterEffectShared.hlsl) explicitly distinguishes water surface masks, scene depth and volume backface depth, and prevents double application of fog. This supports separating medium membership from normal perturbation when designing the observation. It does not justify fabricating missing reflected scene radiance.

Photon was considered as another publicly readable reference, but its [current custom license](https://github.com/sixthsurge/photon/blob/main/LICENSE) contains redistribution restrictions. Do not describe it as MIT/GPL or generally unrestricted OSS. The prior local comparison already covers its Snell branch; no repeated source import or visual comparison is claimed here.

Local consequences are hypotheses. Prior actual Aqualumen trials already rejected another hemisphere-only correction, another fixed subdivision factor, and sparse residual quadrature as sufficient cures. The next experiment observes actual same-draw pre/post normals, Fresnel and transmitted directions before choosing the fix.
