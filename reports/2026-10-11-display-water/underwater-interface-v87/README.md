# Actual underwater interface-side diagnostic v87

Run `display-water-candidate-20261011-v87`, request
`ca7879ce-73de-4c60-b2ad-1a3252d4923d`, disposable world UUID
`b22dbccb-2970-41e6-847f-f183b1ec923d`, Aqualumen Lab.

The diagnostic ZIP changes only the final water fragment output. Original
geometry, wave normals, Fresnel, reflection/refraction ray calculation and
receiver tracing are preserved. NVIDIA compile/link checks passed for this
actual diagnostic pack. Builder exclusivity/preservation tests and runtime
routing tests passed; these are not physical or visual acceptance tests.

Palette, before later compositing:

- Green: transmitted ray exists and neither ray fails the geometric-side test.
- Blue: total internal reflection (no valid refracted vector).
- Orange: valid refracted ray points toward the incident-side geometric normal,
  exceeding the fixed dot-product tolerance 0.00001.
- Red: reflected ray points away from the incident-side geometric normal,
  exceeding the same tolerance. Red overrides the other classes.

Both principal Minecraft PNGs were visually reviewed. The near image has thin
orange bands along parts of the green/blue boundary. The moving principal image
has fragmented green/blue regions and sparse orange boundary fragments. No
large red area was visually apparent. At the initial visual review, no numerical
pixel-area classification had been performed. A positive orange band is evidence of a transmitted-ray/raster
hemisphere mismatch, not proof that it explains the whole folded sky window.
Blue/green fragmentation alone does not establish an optical-law violation.

The moving principal image is one frame from a moving scenario; its whole
sequence has not been visually reviewed. Wave phase/camera orientation differ
from the previous uncolored run, so it is not a pixel-matched causal A/B.

The owned launcher exited with code 0. Collection and exact configuration/Mod
restoration completed without save rollback. No Java process remained. The
ordinary save was not operated on and no diagnostic was adopted into play.

Next: distinguish interface-side mismatch, valid critical-angle magnification
and rays encountering another water interface before changing production
normals or suppressing total internal reflection. Do not relabel a geometric
normal blend as a complete physical water-boundary solution.

Subsequent displayed-palette estimates are retained with image SHA256 in
`displayed-palette-counts.json`. Orange covers 1,717/1,280,000 pixels (0.13414%)
in the near principal image and 1,134/1,280,000 (0.08859%) in the moving principal
image. No red-dominant pixels were classified. The moving image has 217
unclassified pixels. These are post-compositing palette estimates, not raw
shader-status readback or a temporal statistic. Their small area means a
hemisphere correction alone cannot be assumed to remove the broadly distorted
sky window. An additional diagnostic should distinguish otherwise admitted
transmitted rays pointing below the global water horizon; that direction alone
does not prove a second-interface intersection.
