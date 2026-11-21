# Receiver-local cloud lighting — initial checkpoint, superseded

The following is the preserved initial pre-build checkpoint, not current status.
The subsequent [0.8.2 report](README.md) records qualified P/Q and C8 GREEN,
the built ZIP, actual three-view Minecraft run and TEST restoration. Fresh
ordinary handoff and the full visual goal are not inferred from this old note.

This initial checkpoint pursues coherent sunlight/cloud shade; it does **not** accept
natural water/cloud appearance or complete the full realism goal. No 0.8.2 ZIP
or Minecraft activation is recorded yet. Ordinary settings remain selected0.6
with physics0.2, and the client is currently stopped.

## Reproduced source defect

Actual prepare and original terrain VS/FS main run on RTX3080Ti / NVIDIA GL4.6,
fixed phase120, receiver `(0,63,0)`, zenith Sun, cameras `(+/-64,127,0)`.
The old clipped-quad fixtures are INCONCLUSIVE: interpolation fails their
same-receiver qualification before comparing lighting. They are retained, not
classified as shader failures.

A fixed-size one-pixel GL_POINTS receiver delivers the same white albedo,
normal, skylight, world receiver and Sun to the original programs. Its C5
lighting path has no screen derivatives and both relevant input textures are
constant1x1. This qualifies receiver shading, **not broad terrain rasterization**.
Whole C0/C5 observation/repeat differences are0. Two original-source runs
reproduce direct RGB `(5.203125,4.7890625,3.96484375)` versus
`(5.3359375,4.91015625,4.0625)`. The red-channel difference0.1328125 exceeds
the actual16F storage/binary32 allowance0.003993678. Cloudy-cache ratios and
direct-light ratios agree around1.025. Clear-cache inputs match.

Ranked causes were camera-site cloud transmission, Sun-coordinate conversion,
and shadow/numerical state. Qualified fixed normal/Sun/shadow inputs and the
camera-cache response identify the first: terrain sampled one observer-column
cloud transmission rather than the receiving point's column.

## Candidate and incomplete acceptance

The cloud density/integration gains an explicit world-XZ origin; its original
camera-origin overload still drives the unchanged sky/cloud view. Terrain/foam
and direct water glint evaluate cloud extinction at the receiver's own world
XZ and altitude, multiplying the existing separate clear-air C7 cache. The
observer-altitude clear-air approximation, spherical tangent cloud column,
weather closure and cloud morphology are **not** solved by this change.
Missing/incompatible clear LUT input retains the legacy source contract; this
initialization/diagnostic fallback must not be mistaken for proof of the new path.

The first corrected invariant has positive identical C5 on both cameras and
observation/repeat0. P is a thin/clear cloud location: this alone could be passed
by deleting clouds and is therefore **not accepted as the final GREEN**.
Next required evidence is actual prepare-derived positive P/Q receiver-column
source response, propagated cache/target precision bounds, and original deferred
C8 retention. Actual Iris activation, real-view/performance checks and safe
ordinary handoff also remain pending.

The retained native suite passes with the direct-local candidate; legacy
synthetic callers lacking separate C7 still exercise the documented old-input
fallback. This is not full production-path coverage of the new cloud logic.
Per-fragment32-step integration has an obvious performance risk; measure actual
Minecraft before promotion and use a world-grid shadow-field cache if needed.

Source before-change is retained under `build/cloud-local-20261002/before-shaders`;
point REDs, their expanded programs/raw arrays and first invariant candidate
remain in separate immutable build directories. Final archived evidence and
artifact identities will be recorded after the acceptance checks, not inferred
from the source diff. All current implementation/review is Codex work.
