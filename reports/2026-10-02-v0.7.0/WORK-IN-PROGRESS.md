# 0.7 candidate: sampled reflection source retention

2026-10-02 JST. **Native-validated candidate, not installed or Minecraft-accepted.**
Ordinary play remains the verified0.6 ZIP `6ceb9cf0...4c9a73` with benchmark
disabled. Full realistic water/sunlight goal remains active. Codex work only.

## Candidate and causal correction

`dist/Aqualumen-0.7.0.zip` SHA-256:
`09f6fb162a5bbc953f8cdb6860ba3d43410d1969f0aaf12690af9f2dafceee6b`.
Two reproducible builds match; retained0.6 ZIP remains unchanged.
The only executable shader difference from0.6 is an above-water upper-interface
SSR crossing-width correction. Underwater/vertical-face width policy, optics,
march count, four refinements and final sky/surface/confidence guards remain.

The actual-main LINEAR129x129 closed-box fixture at pixel85,49 independently
qualifies the true and biased mirror rays, camera-visible dry wall, constant
palette/tag across all four actual LINEAR source texels and untagged returned
refraction/original-proxy footprints. Paired C4 red+.18 changes no other input.
Before correction, responses are0 /0.0791228115559 against independent Fresnel
gains0.0791228820437 /0.0791228066416. This is a qualified behavioral RED.

Passive observation finds the first endpoint's march overshoot0.4000000954m
exceeds its historical0.40000000596m window, despite a genuine sampled-depth
crossing within the0.47399616242m Z segment. The second endpoint falls just
inside the old cutoff. Allowing the actual last segment width above water
retains both sources:0.0791229009628 /0.0791228115559, errors below2e-8.
The unchanged acceptance tolerance is2e-6. Observer/public C0 difference is at
most3.73e-9. This is the current renderer's **sampled-facet source contract**,
not a finite-pixel rough-BSDF integral or all-silhouette intersection guarantee.
Strict endpoint exclusion remains; exact contacts have not been certified.

Both endpoint negatives pass with public C0 delta0: an off-ray above-water
panel and a deeply submerged tagged bed, after verifying that neither tag
reaches actual transmission/proxy/reflection source footprints. The preceding
default bed probe retains positive reflection and deep-source controls.
[Final full native suite](native/v0.7-final-shore-reflection-native-check.log)
passes on RTX3080Ti/NVIDIA580.173.02/nativeGL4.6, including11 graphics pairs,
three compute programs, all retained optics/atmosphere/wave regressions and
the five Solar cases. No new Minecraft FPS or natural-image acceptance follows.

RED evidence is preserved in the0.6 checkpoint's
[qualified archive](../2026-10-02-v0.6.0/native/visible-reflection-final-qualified-red-artifacts.tar.gz).
The first tag-boundary fixture failure is separately retained and is not RED.
[Final GREEN inputs/outputs](native/final-visible-reflection-green-artifacts.tar.gz)
and [candidate source/tools](native/candidate-source-and-validation-tools.tar.gz)
identify the current experiment. Earlier uninstalled draft used wider scope;
its ZIP remains privately in `build/`, not selected or mistaken for this SHA.

## Separately reproduced, unresolved optical-depth defect

The new opt-in `--water-optical-depth-only` exercises the unchanged production
vertex/main with a fixed wall and local bed. Only a remote submerged box along
the original camera ray changes. Independent closed-box intersections, whole
2x2 raster geometry/facet equality, actual sampled wall IDs, camera visibility,
red-only positive response, repeat and observer neutrality qualify pixel56,38.
Both states retain source edge/confidence1. The real local bed stays at about
1.17m; screen-estimated depth instead changes0.25→1.1776848m.

Public source response changes0.0987982600927→0.1180650740862: difference
0.0192668139935, versus float/repeat allowance7.8678131e-6. Recomputed optical
Fresnel explains the two gains, while actual geometry/local water depth is
unchanged. The [frozen0.6 run](native/water-optical-depth-v0.6-frozen.log) and
[0.7 candidate run](native/water-optical-depth-v0.7-first.log) reproduce the
same failure at the same pixel. This is not introduced by the SSR correction.
[Raw fields and geometry](native/qualified-remote-depth-red-artifacts.tar.gz)
are preserved. Absolute true-raster-facet Fresnel is a reference, not an oracle
that incorrectly forbids all intentional small-wave shading normals.

This RED is intentionally opt-in and remains unresolved. A global depth64
override is not shipped to obtain GREEN. Next implementation must make local
water depth/geometry/optical normals coherent, preferably using read-only loaded
world bathymetry in the dedicated bridge, and verify actual natural views.

## Other evidence boundaries

The fresh stepped diagnostic still contains other large switches. The new
pixel65,47 point hit is camera-visible, but its projected error footprint crosses
a genuine bank edge: the visible-bed qualification rejects it. That failure
is **not a behavioral RED**, and no extra refraction iterations/best-hit shortcut
was applied. New SSR controls likewise do not certify arbitrary bank silhouettes.

## Frozen native provenance

- Water fragment SHA: `6f7d060c3be774dfe44259fb403015b9dce14b36209b3f0ace1be26a0bb94b78`.
- Native harness SHA: `31595869eff023d6461142dbb0c1acbdcecfc3e77397cc91b2f25b6d3f8cc9dc`;
  executable: `9dc27e50ddb70b38e19595ec7d4d54ac2ea24d3ba0138b21b739284b6158ea14`.
- Optical-depth header: `da18d34521faea45859123b78a226eb3910d40277da7acd77ffcf3e6f40a1604`.
- Final native log: `42a2972a4afed8284ac877d1b5fc2f55b7f95ee476bb2801c79b287cfcbe96dc`.
- Candidate source archive: `1b39454580782773e602c7fc93907f406b51674c0022237c97b3b3bba7105d04`.
- Final reflected-source GREEN archive: `b705a66cdd0733f384abc914b528b50a072bb66576e255b5b77d54f6d50fdefc`.
- Paired0.6/0.7 unresolved optical-depth RED archive:
  `3c8e80abf4ee8612ff5fd995cb1e1a31611f64e98a5837b7ec77998c4b9b51cd`.

The source archive identifies these native experiments; future harness changes
must not be assigned retroactively to these logs. No ordinary-save/config/account
data or normal launch argv is in these archives.

Still required: real Minecraft activation/images/motion for this exact candidate,
natural coast/river appearance, local-depth correction, natural rowing/wakes,
spatial cloud-light coherence and other full-goal requirements. Current normal
world/process/settings were not altered by these native tests. The prior TEST
shutdown stall remains unresolved; no new TEST lifecycle took place here.
