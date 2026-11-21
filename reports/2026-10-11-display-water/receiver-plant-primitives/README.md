# Plant primitive intersection foundation — CPU only

The v52 actual-game unknown-subtype images identify vegetation as a substantial
reflection coverage limitation. The ordinary source capture still admits only
full opaque UP faces. Skipping a whole plant voxel would therefore bypass an
actual foreground leaf and is not the chosen correction.

`ReceiverQuadIntersection` introduces double-sided triangle intersections for
owned quad positions and UVs, nearest nontransparent primitive ordering, and
explicit opaque/transparent/unknown alpha coverage. Transparent samples continue
to later geometry. Unknown coverage blocks later geometry rather than borrowing
floor radiance. Exact equal-distance unknown coverage takes precedence over an
opaque sample regardless of list order. Unit ray directions make distances and
range limits comparable. Finite-input and interpolant guards reject malformed
geometry/rays. Positions are not clipped to a block-owner voxel.

Validation performed:

- `bash tools/test-receiver-quad-intersection.sh`: CPU synthetic first-leaf,
  transparent-hole, nearer unknown, equal-distance unknown, backface, parallel,
  outside-quad, behind-origin, range and nonunit-direction cases.
- `bash tools/test-receiver-sodium-scope.sh`: existing owned source-scope CPU
  fixtures remain passing.
- `git diff --check`: no whitespace errors.

This is not wired into the live producer or shader. It provides no evidence of
Minecraft visual improvement, NVIDIA intersection parity, actual texture alpha,
material radiance or runtime speed. Existing normal packs/settings are unchanged.
The tests supply synthetic alpha callbacks, not Minecraft texture samples.

Next required integration: capture all actual plant quads with renderer/world/
frame/resource ownership, retain their actual UV/texture and lighting data, assign
intersectable primitives to every overlapped spatial cell, and prove GPU first-hit
ordering against opaque banks and transparent texels. Incomplete model or texture
capture must preserve an unknown barrier. Only then may qualified plant cells
replace the current whole-voxel unknown fallback. Existing cube-face qualification
must remain unchanged; diagonal plant normals cannot masquerade as an UP receiver.

## Owned Sodium model capture API

`ReceiverSodiumScope.openGeometry` now retains every synchronous model quad,
including UNASSIGNED and non-UP faces, as immutable copies of raw xyz, atlas UV,
color, AO and packed-light inputs with the actual renderer offset. The snapshot
retains epoch, cell and state identity. Empty, malformed, foreign and greater-than-
256-face captures fail closed. This separate mode never produces an ordinary
cube radiance snapshot or requests the existing Iris packed-source encoder hook.

`OwnedSodiumReceiver.Session.captureGeometry` uses the existing owned, cloned
Sodium section/renderModel path for exactly seagrass, tall seagrass, kelp and
kelp_plant. Unsupported unrelated blocks are not admitted. The existing opaque
UP capture remains its own mode with its packed encoder qualification unchanged.
No live field producer calls the geometry API yet. No plant cells are reclassified.

Additional validation: expanded scope CPU fixtures verify arbitrary face capture,
defensive copies, epoch/offset retention, no cube-source admission, foreign world,
state mismatch, malformed vertices/offsets, separate-AO rejection and capacity.
The full Mod compiled as
`build/aqualumen-physics-0.3.0-plant-owned-model-v60.jar` (not installed).
Actual plant model capture in Minecraft and texture-alpha/resource ownership
are still unverified; this build is not evidence that the new API succeeds live.

Later checkpoints supersede that build-only statement: v53 proved raw all-face
capture for actual seagrass/tall_seagrass; v54 proves every such face receives its
owned Iris encoder output and can be decoded with actual terrain uniforms. The
current geometry mode therefore requires complete encoding, unlike v53's raw-only
mode. See the sibling v53/v54 reports for narrowly scoped runtime evidence.
Actual texture alpha, plant lighting and GPU first-visible-primitive attribution
remain open; no live receiver field reclassification is made by these probes.
