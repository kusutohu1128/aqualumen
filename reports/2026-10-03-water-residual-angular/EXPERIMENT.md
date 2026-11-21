# Residual directional-source angular diagnosis

2026-10-03 JST. Previous goal turn is **progress**, not a completion: the
TEST operator, invalid-covariance fix and actual six-view comparison are
implemented/recorded. The frozen residual-interface packet's 1,514-entry
manifest rechecks PASS this turn. Its appearance is explicitly not adopted.
All full water/sun/cloud/shore/motion requirements remain unchanged and active.

## Reproduction and ranked predictions before execution

Saved TEST near/deep/tilt C0 views have separate small bright solar points;
CONTROL has one compact Sun. Root re-viewed the saved near TEST this turn.
The prior native directional fixture had a bright LUT cap and zero Sun cache,
so that GREEN does not test these solar replicas.

1. Sparse finite angular quadrature: each of nine facet rays can form its own
   narrow source image. A derivative-free narrow source should retain aliases;
   denser rules should change their positions/magnitudes on a common valid
   domain and approach a separate integral. A higher node count alone is not
   a convergence or visual-quality pass.
2. Native solar pixel coverage coupling: gnomonic dFdx/dFdy follows each node's
   transmitted ray, and the safe TIR ray can change neighboring derivatives.
   Reproduction without those derivatives excludes this path for that bounded
   reproduction, not for all critical/rim cases.
3. Whole-operator eligibility/domain rejection: one nonfacing, wrong-hemisphere
   or opaque node returns the parent color. If replicas coincide with applied
   transitions, source refinement alone is not an isolated diagnosis. Require
   actual common eligible/valid/applied flags before interpreting comparisons.

## Controlled-source seam and fixed policy

Use the frozen guard-v2 helper (def6b357...bbfd9c) and pinned resolved-normal
parent (3a83e837...ab26), actual VS/TCS/TES/FS main, factor4/phase120. No shipping
source changes. Original mean, covariance, Fresnel/TIR, IOR1.333, receiver
tracing/return policy, source units and wave geometry stay fixed across rules.
Any fixture/observation transformation must recover its exact source seam;
retained original packets and earlier RED/INCONCLUSIVE evidence stay unchanged.

TEST-expanded FS alone substitutes standard-normal GH9/GH17 rule constants
for GH3 and its declared order guard. Positive tensor probability weights;
no hidden-node flipping, survivor renormalization or covariance adjustment.
Changing rule extremes may change all-or-nothing validity; that is reported,
not silently fixed. Double rules are independently Gaussian-moment checked.

Replace the exact environmentSkyRadiance return with sampleSky(lut,ray) plus
a controlled source. Uniform black ordinary sky LUT/cache, known4m column,
zero gradient/ripple and existing zero opaque source fixture. The controlled
source is zenith (0,1,0), dyadic peak RGB(.25,.125,.0625), CHORD Gaussian
exp(-dot(normalize(ray)-zenith,normalize(ray)-zenith)/(2*sigma*sigma)).
Widths .00465/.08, constant and dark controls are **fixed peak radiance**,
not fixed integrated source power, native solarDisk or calibrated solar beam.
Gaussian/constant C0 minus same-rule dark C0 isolates source response. This
synthetic source deliberately avoids solarDiskCoverage's pixel derivatives.

Actual observation semantics: C0 final color; slot1 mean normal/grazing;
slot2 covariance/effective footprint; slot3 coefficient mass/R/T/TIR;
slot4 valid/applied/minFacing/opaqueCount; slot5 actual viewToEye/eligible
(new semantics, not old source masses); slot6 known/upper/underwater/water;
slot7 scatter/eligible. Geometry/inputs/matrices are archived. Observer removal
must recover source bytes, repeats exact. Upfront passive C0 abs5e-4+rel2e-4,
depth2e-6; finite coefficients abs2e-5. GPU vs same finite-rule double arithmetic
source gate abs2e-6+rel2e-4 per RGB component is a local fixture policy, not a
GLSL transcendental or physical-energy theorem. Failure/absence is preserved.

Before any new GPU output: cross-rule/source mean-normal, view-to-eye and scatter
identity uses local binary32 abs+rel8*2^-23, with observed maxima reported.
Grazing/eligibility bits, covariance/footprint, flags, geometry, depth, matrices
and input snapshots remain exact. This fixture arithmetic policy neither
changes the source-response gates nor reclassifies any prior strict RED.

CPU saved-map descriptive policy is fixed before output: integer disk ROI
radius40 centered(128,128), positive source-delta luminance weights
(.2126,.7152,.0722), eight-neighbor components above .2 of ROI peak.
Component count is descriptive, not a subjective or physical quality gate.
Use actual common eligible/valid/applied domain across all compared rules;
do not renormalize surviving pixels/nodes or call a new rejection a visual cure.

Independent continuous reference integrates the original Gaussian slope
measure over a declared finite standard-normal square, with explicit omitted
projected tail/radiance bounds, support-seeded numerical refinement and local
convergence abs2e-7+rel2e-4. Reference finite-window domain validity is separate
from each finite helper rule's domain. No Gaussian-tail masking, Smith,
multiple scattering, energy/reciprocity or natural-Iris acceptance is inferred.
References: [DLMF quadrature](https://dlmf.nist.gov/3.5),
[PBRT rough dielectric](https://www.pbr-book.org/4ed/Reflection_Models/Rough_Dielectric_BSDF).

## Lifecycle before GPU execution

Current ordinary0.6/physics0.2 paused F2 09:48:22 freshly viewed. Normal config
snapshots copied into private cache. SaveQuit09:48:56 saved all three dimensions;
title F2 09:49:31 separately captured/viewed before Quit click. Owned launcher
session92068 exits0; host Java3837452/prismrun3837377 absent, then all Minecraft
JVMs absent. Fresh ordinary post-save tree is comparison-only backed up, never
restored. No ordinary camera/time/terrain automation. Native GL is root-only
and only with every Minecraft JVM absent; agents perform CPU/source work only.
Private launcher output is never copied into this public packet.

Safe handoff after native work: verify normal config bytes and ordinary save
tree equal the fresh post-save snapshots; no backup restoration. Reopen normal
0.6/physics0.2 without instrumentation, pause and view a fresh F2 in separate
invocations. No native GL after the ordinary relaunch.
