# Underwater primary-source comparison — 2026-10-11

Read-only code review, not runtime comparison. No shader-pack source was copied
into Aqualumen or installed. Current upstream commits were checked via their
primary GitHub APIs.

## Photon

[Translucent shader, commit 15458c0937f8647c37eb6a501bef5eb3bf3da31b](https://github.com/sixthsurge/photon/blob/15458c0937f8647c37eb6a501bef5eb3bf3da31b/shaders/program/gbuffers_all_translucent.fsh)
contains the optional Snell-window branch. Underwater, it evaluates dielectric
Fresnel using the air/water index ratio and blends fragment alpha toward full
opacity. This separates the underwater reflection/transmission qualification from
merely distorting the whole screen. The same file writes tangent-normal refraction
data and applies a separate fog contribution. These observations alone do not
establish all offscreen receiver handling or natural-view quality in Photon.

## Complementary Reimagined

[Water material, commit c09950df0650b27dac260c1b0f69afc11387aa6f](https://github.com/ComplementaryDevelopment/ComplementaryReimagined/blob/c09950df0650b27dac260c1b0f69afc11387aa6f/shaders/lib/materials/specificMaterials/translucents/water.glsl)
adjusts perturbed normals toward the geometric normal when reflection points into
water. Its underwater material branch has style-dependent transmission attenuation
using Fresnel powers, and reflection scaling differs for world-space-reflection
configuration. This is a broader artistic material policy, not evidence that
every branch implements Aqualumen's exact transport model. Other passes were not
comprehensively audited, so no global absence/presence of physical TIR is claimed.

## Consequences for Aqualumen

Aqualumen already has directional refraction and exact Fresnel/TIR machinery;
copying an alpha heuristic would not fix missing first-hit geometry or prove
complete model ownership. The fresh v77 natural images still show the folded rim
and dark polygonal exterior. Keep geometry/source and optical-normal questions
separate. Any normal-policy change must be bracketed by production tests around
critical incidence and then judged on original natural images and motion.
Retain actual optical ray directions, water membership and paired source radiance;
do not replace unknown receivers with invented environment color merely to soften
the image. This comparison does not constitute visual acceptance or completion.
