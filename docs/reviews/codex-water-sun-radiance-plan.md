# Next tracer bullet: above-water receiver-Sun radiance units

This is a source-derived plan, **not a GPU RED or shipping correction**. Finish
the receiver-local cloud slice first. Natural cyan/shore appearance is not
accepted from either this calculation or the fixed-wave source-retention PASS.

`lighting.glsl` produces C5 as `albedo*E_air/PI`; deferred preserves it in C8.
The water incident-beam correction applies Fresnel admission and Beer loss to
that dry Lambertian receiver reference. This changes the incoming power and
therefore its water-medium receiver radiance. It must not receive an arbitrary
index-squared irradiance multiplier. The distinct exiting directional-radiance
conversion is what the next test should check.

The [PBRT4 dielectric model](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF#sec:non-symmetric-scattering)
distinguishes radiance conversion from power conservation at refraction. Applying
that convention to the current **known direct receiver component** predicts an
air-side exit factor `(n_air/n_water)^2`, in addition to existing Fresnel/Beer.
This is an inference about the declared source units, not proof that all C4
ambient, proxy or scattering sources already obey those units.

Use actual original VS/FS main, a confirmed horizontal bed, flat interface,
zenith Sun, vertical viewing ray and depth1.5m. Paired inputs are C4=B+D/C8=D
versus C4=B/C8=0; hold caches, reflection, glint, shadow and scattering inputs
fixed so their common contribution cancels. With D=(0.2,0.15,0.1), clarity1,
index1.333 and the currently declared extinction, the independent tagged gain
is approximately `(0.04135884,0.06277796,0.04862506)`. Existing source algebra
predicts approximately `(0.07349006,0.11154947,0.08640133)`, or1.776889 times
as much. Derive final bounds from actual supplied/read-back D, confirmed source
path/footprint, Fresnel and C0 quantization; these rounded numbers are not gates.

Require independent first-bed hit/confidence/normal/path, positive all-channel
response, zero-source and reflection-tag controls, whole-image passive-observer
neutrality, repeat equality, and an actual C8 source paired with C4. Preserve
the before failure. The existing depth-ratio test cancels a constant exit factor
and cannot certify these absolute units.

If verified, a **direct-component-only** exit correction can preserve the
synthetic intrinsic C4/no-C8 first-visible-bed contract and existing no-Sun
controls. Do not globally dim the frame or silently apply the factor to opaque
air proxies, ambient/scatter, underwater receiver irradiance or reverse air-sky
entry. Those conventions need their own directional/flux tests. This factor
is achromatic: it does not by itself fix cyan hue or shore serrations.
