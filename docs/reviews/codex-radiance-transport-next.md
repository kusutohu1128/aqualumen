# Radiance convention: next physical test, not a shipping correction

The actual0.8.1 coast/river images still have strong cyan and pointed dark bands.
The source atlas establishes that much of the cyan is transmitted bed light;
the saved terrain also establishes real metre-scale depth. Neither observation
licenses shortening every path, changing saturation, or adding an arbitrary
brightness factor.

The [PBRT4 dielectric model](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF#NonSymmetricScatteringandRefraction)
derives the squared-index change in transmitted radiance and distinguishes it
from conserved flux. Its camera-path dielectric throughput accounts for that
index ratio. This is a reference for a future test, not a claim that our current
opaque C4, Sun C8 and scattering closure already share the requisite convention.

Current water main mixes `(1-F)*refraction + F*reflection`. There is no explicit
medium-index radiance conversion. Whether a missing factor is an actual defect
at a particular call site requires stating what each source represents: intrinsic
submerged-surface radiance, dry-lit reference radiance, or air environment
radiance. The C8 incident-beam correction is an irradiance/receiver calculation,
not automatically an air-to-water directional-radiance conversion. Do not simply
multiply the entire water color or Sun term and call energy calibration complete.

After the currently prioritized wavy first-visible-bed behavior, use one
production-main tracer bullet with a qualified visible intrinsic Lambertian bed
source, zero incident-C8/environment/reflection tag contribution, exact Snell/Fresnel,
and an independently stated medium-radiance unit. Compare the absolute tagged
C0 response with the derived exit-index and Beer factors; require a positive
reference, actual returned first face/path and all quad inputs. Preserve before
failure and guard the source convention before any implementation change.
Only then add an independent underwater air-sky entry/angular-flux control so an
apparent gain correction cannot manufacture energy or be applied twice.

This is Codex source analysis/inference. No index-factor shader change, GPU
result, natural-view improvement or broad radiance/etendue acceptance is claimed
by this note. The natural-shore, coherent-lighting and motion goals remain open.
