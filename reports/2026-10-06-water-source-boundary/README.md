# Reflected-source viewport-exit omission: original MAIN RED/GREEN

2026-10-06 JST. This goal turn makes concrete diagnosis and renderer-correction
progress. The full `docs/REALISM_GOAL.md` objective remains **unachieved**.
No candidate ZIP/Mod installed or ordinary pack changed. Normal selection is
still0.6/physics0.2; the modified renderer source is a development candidate.

## Actual evidence, not a source-visibility assumption

The previous probability8/12 source divergence is reproduced with an original
four-stage tilted native water MAIN, actual six-metre opaque depth/C4, queried
matrices/stages and fixed actual n/v/C context. A new TEST-only SSBO records each
reflected node's raw weight/ray/facet/origin, tracer result, source, terminal
reason and first depth-crossing bracket. It changes no optical output:
all eight MRT/depth images and repeat bits match baseline exactly for both tags.
The reader checks actual storage offset16/stride16/vec4 type, typed source maps,
stage identities, negative untouched storage, raw controls, independent forward
probability/optics, rigid matrices and per-node returned-source radiometry.

The independent oracle solves ray intersection with the declared observed
view-plane and projects that point; it does NOT replay GLSL SSR stepping. The
actual sampled depth map is constant and matches that plane. This establishes
first-plane visibility for this fixture, **not arbitrary hidden/offscreen world
geometry or a Minecraft first-object proof**. Original n/v/rays are not repaired.

| Rule | Recorded R nodes | Old hits/misses | Known in-viewport misses | Fixed hits/misses |
| --- | ---: | ---: | ---: | ---: |
| Probability8 |128|40/88|1|41/87|
| Probability12 |288|91/197|6|97/191|

All known misses exit at a coarse viewport endpoint BEFORE sampling the visible
receiver along that segment. No first crossing is rejected by depth width in
these missing nodes. Weight/distance/source replay passes. Original128-source
diagnosis alone understated the weighted loss; the288-node condition supplies
six materially weighted misses. This supports the viewport-exit hypothesis,
not a permission problem, probability-mass fit or thicker depth acceptance.

## One-variable physical correction, failure retained

Before changing code, `first-plane-optical-red.log` fails on six known misses.
The correction clips ONLY the last segment from a valid previously observed
endpoint to the viewport boundary. Sixteen projection bisections select a
strictly in-frustum endpoint; the exact old viewport, before-surface, crossing
width, four-step hit refinement, above-water receiver and source guards remain.
After inspecting that final segment, an unhit ray terminates: never sample or
declare an object outside the observed buffer. No density/normal/C/index/source
units, Beer extinction, quadrature, survivor probability or threshold changes.

`first-plane-optical-green.log` passes with0 known misses and0 hits outside the
oracle's safety viewport. Strict old/fixed comparisons retain EVERY previous
positive hit and its returned source/path exactly. They recover ONLY the known
misses, leave all absent/outside nodes absent, and retain all raw node fields,
input maps, depth/geometry and selected diffuse transmission exactly.
The288-node comparison verifies3198 exact selected/input comparisons.

The identical qualified `reflectionTrace` function is now implemented in
`shaders/gbuffers_water.fsh`. Its SHA256 is
`99d5a541c4bcc6f45869be60b74e79f9aa8d0d118ba6ba5d5cda943e0a44c158`,
matching the actual native baseline fragment function byte-for-byte.
The full current `make check` passes11 retained program pairs and production
regressions on RTX3080Ti / GL4.6 NVIDIA580.173.02. TEST observation code is NOT
included in the production source. No modified candidate is selected in Iris.

## Do not confuse a recovered receiver with integral/visual acceptance

For probability12, captured green changes .06806848198 -> .07515259087.
The SAME128/288-node independently intersected-plane sums are .07364639175 /
.08052458763. Those omit the legacy viewport-edge/confidence fade, so they are
NOT interchangeable shader-response references. All retained weights and the
actual returned source/Beer attenuation replay; the original edge/confidence
blend remains. This fix does NOT by itself prove directional-source quadrature
convergence, correct legacy radiance units, physical energy or offscreen light.
The old dense .0729541704 is an OLD tracer result, not corrected physical truth.

An affected new dense source packet is retained separately after this change:
green .07443220913,7107 hits/7842 explicitly counted misses,113 independent raw
controls. It is a96-order finite dense rule, NOT a certified integral truth.
Corrected probability8 .07349345833 is about1.261% below that response;
probability12 .07515259087 is about0.968% above it. **Few-node directional-source
convergence is still rejected**; no earlier gate is relaxed or replaced by1%.
No new native timing, Minecraft FPS, natural-scene appearance, moving-camera/
contacts or Iris activation for the modified renderer is claimed here.
General/critical receiver coverage and practical efficient source integration
remain open, alongside full shore/cloud/volume/radiance/weather/night/energy/
motion and physical-simulation requirements.

## Preservation / lifecycle

Original launcher16740 / Java3202154 saved all dimensions13:07:38 and cleanly
exited0 before new GL. The fresh41-file baseline is `prelaunch.json` and its
private cache is comparison-only; no ordinary save restore or camera/time/
terrain automation. Prior sealed Evidence and unrelated dirty work are retained.
Restoration-before-relaunch verifies41 ordinary saved files unchanged, original
configuration bytes and active Mod hashes. The owned normal launcher54078 /
Java3220839 is freshly reopened, with exact ordinary lockFD154 and original
0.6/physics0.2 selection. Root inspects runtime13:24:07 and pause13:24:13;
live-process and configuration qualification is recorded in `checkpoint.json`.
Save identity is historical after normal reopening; no save is restored.
No native GL occurs after this handoff. The affected ten-case MAIN source pack
is prepared but NOT executed here; [RESUME.md](RESUME.md) records that next step.
No new Claude/subagent invocation, commit or push. The preexisting OpenAL device
failure remains separate and unfixed.
