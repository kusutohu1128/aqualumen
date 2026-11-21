# TEST-only known-column optical-normal ablation

Pre-observation plan, 2026-10-03. Not a shipping fix or visual-quality acceptance.

The shared atlas/MRT instrumentation and common analytic `frameTimeCounter=120.0`
input are identical. Only the known-column water-FS assignment differs:
`n=normalize(vec3(-wave.y,1.0,-wave.z));` versus `n=rasterFacet;`.
VS, IOR, local-column admission, grazing, trace arguments and transport remain.
Contact/ripple solver, bathymetry, entities, weather, Sun and observer clock are
not frozen by the macro. Same-camera screenshots are not a pixel-paired replay.

Run only in the opt-in Aqualumen Lab, AqualumenNaturalV2 UUID
b22dbccb-2970-41e6-847f-f183b1ec923d, seed 308060, natural noise overworld.
Ordinary world is saved and quit before GPU work; no ordinary camera/time/terrain
automation, no save restore. No terrain placement in this experiment.

Hypotheses, in priority order:

1. Short analytic slopes retained by the FS but removed from the metre-grid VS
   produce high-frequency Snell/TIR folds. Facet should reduce fine wrinkles.
2. Underwater SSR miss falls back to constant scatter. Dark exterior can remain
   in facet, with sample Fresnel near one and negative reflectedHit.a.
3. Critical-angle refracted cloud sampling lacks angular-footprint integration;
   residual rim aliasing can remain after facet. This test does not isolate it.

Native checks are compile/link only. Actual Iris near/deep/tilt views use 1600x900,
10-second warmup and 5-second timing sample. Diagnostic cost excludes FPS claims.
Final atlas uses active C9/C10/C11 scalar samplers; C0 is post-composite tone/gamma
without final AA. Compare shared top-left panels, not atlas versus normal final.

Selected raw level-zero texels, fixed before observing either pack (bottom-left
origin): interior (801,451),(401,451),(1201,451),(801,251); edge envelope
(33,451),(65,451),(129,451),(193,451),(1409,451),(1473,451),(1537,451),(1567,451),
(129,129),(1473,129),(129,771),(1473,771).
Nonvacuous near-view minimum: interior 4/4 and at least 4 edge-envelope points in
both packs with C9 alpha=known, C10 underwater=1 and water-mask=1, finite values,
actual bound RGBA32F C9/C10/C11 at 1600x900, authorized scope and restored GL state.
Report excluded points explicitly; do not choose replacements after seeing results.
Do not generalize selected SSR misses to the whole image. Named FINAL geometry
uniform inactivity is not proof of runtime geometry attribution. Observer captures
and PNGs may be different frames; report actual camera/observer time separately
from fixed shader phase. A naturally circular Snell window is not a defect.

Additional pre-facet qualification: all 16 selected known/water/underwater flags
must match between packs. At least 4 qualified points, including at least 1 edge
point, must have max absolute optical-normal component difference above 0.001.
Report Fresnel differences and changes in F>=0.9999 separately; SSR state need
not change. This is an ablation diagnostic, not a physical quality threshold.

Status: builder CPU tests pass; both generated packs compile/link on the native
GPU. Control loaded in actual Iris. The first queued request was consumed before
the integrated server existed and aborted; its status is retained. The same
live JVM then completed a requested near view. Its later raw observation has
16/16 known+water+underwater samples, bound RGBA32F targets and restored state.
The top-right panel is dark purple from downward encoded normals, not the bright
magenta unknown marker. Initial visual interpretation was corrected after raw
known=1 measurements; the original record and extra near repeat are both retained.
Both actual Iris packs now completed near/deep/tilt captures. Root reran the
saved-evidence audit, which is byte-identical to the independent audit. Each
pair has 16/16 qualified points and 16/16 optical-normal responses above .001,
including all 4 interior and 12 edge points. See runtime-audit.json for exact
values and the README for the appearance decision. Facet is not adopted.
