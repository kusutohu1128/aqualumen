# Conditional transmission-only Sun experiment

Plan only; no shader, tool, GPU or game change. Proceed only if the saved actual Iris
reason capture establishes **firstReason=3 (reflected hemisphere)**, not the combined
hemisphere count. Do not reclassify the existing fixed-16/minimum-4 negative result.

**Public RED seam.** Extend the actual four-stage production-main fixture from
`tools/water_residual_sun_probe.cpp:42` with a removable TEST-only wrapper-argument
injection, identical in control and candidate. Do not duplicate the optical helper
or assign the global normal/ray used by earlier FS calculations. Use binary32
`meanNormal=(0.7682212591171265,-0.6401844024658203,0)` and
`viewToEye=(0.2923716902732849,-0.9563047289848328,0)` at the actual
`waterResidualSunInterface` call. These are constructed slope-1.2/17-degree inputs,
not an observed water facet or camera ray. Keep actual covariance, footprint,
geometry/tessellation, phase120, bathymetry, view origin, scatter and all eight
samplers. Predeclare center `(128,128)` plus the existing five additional fixed
Sun pixels; do not search/shrink after execution. FOV2, clear weather, Sun up,
NEAREST/base-level open depth1, skyAccess1, cache RGB `(0.5,0.625,0.75)` versus
zero cache retain stock beam `(9,11,12.75)` and radius `.00465`.

**Nonvacuous prediction and admission.** At the existing native covariance
`(xx,xz,zz)=(.006807451602071524,.0027949956711381674,.002802651608362794)`,
independent double arithmetic gives all nine unchanged legacy GH3 nodes facing
the eye and reflected downward: minimum facing `.803267`, maximum reflected-y
`−.00035948`, minimum transmitted-y `.994923`. Conversely every positive 4×12
Sun-cap node has reflected-y `.035379.. .056300`, transmitted-y above `.999989`,
and finite non-underflow slope density (maximum quadratic `14.5525`). Removing
only the cap reflected-y condition predicts sharp transmitted RGB
`(17.8005784121,21.7562625037,25.2174860838)`; independent 8×24 and 12×48 rules
agree within `8e−11`. Require each isolated channel **>1** and the existing
absolute `2e−6` + relative `2e−4` oracle gate; reference convergence remains
absolute `2e−8` + relative `2e−6`. Actual queried inputs and full/base old-applied
status must qualify first. Different covariance, trace weights, failed old domain
or float boundary checks make this proposed fixture INCONCLUSIVE, not tuned PASS.
Isolate positive-minus-zero C0 and subtract the measured unchanged legacy
`R * (scatterPositive−scatterZero)`; cache also changes scatter. Do not zero
scatter or assume stock derivative-filtered GH3 sunlight is exactly absent.

**One model change.** The control must produce an actual linked-main numeric RED
against that positive reference, with cap firstReason3/application0 and both old
full/base calls independently applied. The candidate removes only
`&& reflected.y<0.0` from `water_residual_sun_cap.glsl:113`. Keep transmitted-y,
raw n/v, inverse reconstruction, strict SPD, Fresnel, all receiver predicates,
48 positive nodes and saved-full rollback unchanged. Preserve the two
unconditional old calls and their original hemisphere/visibility gates. Repeat
C0/depth/geometry/observer passivity checks; featureApplied1 alone is not success.

**Independent opaque-transmission negative.** With the same injected inputs and
candidate, change only depthtex1 to a central opaque patch covering actual cap-ray
projections (predeclare radius64 pixels, view-z plane `−2.5`; all other depth1).
The old GH3 transmission rays are analytically `1.18775..5.77580` degrees from
zenith, outside the cap `.26643` degrees. Nevertheless require actual old full/base
application and cap `kind==1`/reason6 before accepting this negative: application0,
whole saved-full C0 rollback, no surviving-node normalization. If the patch also
breaks the old domain or fails actual trace convergence, report INCONCLUSIVE.

**SSR boundary and limits.** Keep `reflectionTrace` and `reflection.a<=0`
(`water_residual_sun_cap.glsl:136–140`) unchanged. Open depth should yield its
miss alpha; this is a required observation, not inferred visibility. If reason7
then blocks the candidate, retain that result and propose a separate experiment;
do not remove reflected-y and SSR alpha together. This fixture can qualify only
the bounded transmitted-source condition. It does not accept geometric normal
consistency, arbitrary/narrow SPD, rim/critical/offscreen visibility, native
pixel-AA equivalence, energy/reciprocity, natural appearance or shipping physics.
