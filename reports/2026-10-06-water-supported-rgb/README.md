# Supported RGB interface: actual MAIN OLD RED → controlled GREEN

Status: concrete implementation/integration progress, **not natural-water or
shipping acceptance**. Previous goal turn was progress (original-MAIN OLD RED
and supported-T GLSL port); this turn adds separate nonblack reflected and
transmitted contributions and observes their corrected responses in actual MAIN.
The full `docs/REALISM_GOAL.md` goal remains active/unachieved.

## Correction and actual native seam

The new TEST `water_supported_rgb_test.glsl` combines supported air transmission
and water reflection independently. It does not add a red test tag to existing
`originalColor`. Transmission uses the retained analytic light-domain partition;
reflection uses correlated Gaussian forward slopes, separate facing/world/macro
support, Fresnel/TIR, projected-area weighting and Smith visibility. Critical and
reflection-horizon roots partition the z integration, with a cosine coordinate
map and compensated sums. The8-sigma square keeps original density, not survivor
normalization. Shared raw n/v/C and source units are unchanged.

The [original optical RED](../2026-10-06-water-supported-glsl/main-old-01-audit.json)
has source response0 at actual Iris input1114,155. The new actual four-stage
native MAIN executes its new interface at that matched input. Source-control
callbacks provide red0.25 air and green0.125 water independently; reflection is
explicitly not presumed black. Actual C0 responses in both runs:

| Source | Actual red C0 | Actual green C0 |
| --- | ---: | ---: |
| zero | 0 | 0 |
| air only | 0.00610337825 | 0 |
| water only | 0 | 0.12108475715 |
| both | 0.00610337825 | 0.12108475715 |

Both source-response gates pass independently: transmitted red differs from
the sealed model by2.482e-8; reflected green differs by2.837e-7. Blue remains0.
The corrected C0 is the returned R+T integral, not old color plus a positive tag.
Disabled eligibility, explicitly unknown source and unsupported zero covariance
return exactly the original C0 map. Zero covariance is a degenerate model input,
not intrinsically invalid water; its general physical closure remains open.

The TEST evaluation ROI is explicitly **one native pixel128,128**, not a
production cutoff/blur/window rule. Original MAIN and four geometry stages still
execute; outside that ROI the captured C0 is unchanged. This is a selected
actual-MAIN correction, not proof of every pixel's bands or whole-Iris scene replay.
Callbacks are controlled radiance sources. Actual receiver tracing, full sky/
Moon/native-Sun48 source routing and production adapter are **not yet validated**.
The general operator cannot safely be shipped with these fixture callbacks.

Independent raw replay verifies136 exact comparisons in the final audit (135
in the earlier reader), including full
repeat/depth maps,8 uploaded source maps, fresh direct TES C4 bits against the
retained original parent, disabled C0 bits against that parent, actual n/v/C/eta
and queried four-stage source hashes.
New positive/negative applicability, source-known and raw input bits are checked,
not just producer success flags. `main-01` qualifies the first integrated core;
`main-02` additionally rejects invalid/zero ray callbacks. Absent/zero weighted
nodes are skipped individually before source queries so they cannot masquerade
as a globally unknown source. No physical receiver hit/miss proof is inferred
from that callback-domain control.

## Reflection reference / tests

New CPU forward reflection and independent inverse reflection mapping retain
raw-view length explicitly. The node's slope-to-solid-angle Jacobian is
`length(v)/(4*dot(v,m)*abs(m.y)^3)`. Finite-difference and forward/inverse node
tests pass, as does analytic partition classification at5005 independent points.
At the4 actual inputs, partitioned slope orders96/128/192 refine within the
unchanged `2e-6+2e-4*response` gate. Reflection values are approximately
0.926991/0.949856/0.968680/0.972784. Tail bounds follow the retained Gaussian
projected-area bound. These are numerical refinements and selected-node checks,
**not an independently integrated second full reflection domain, rigorous
quadrature intervals, full radiance/energy/reciprocity or multiple scattering**.

Five new CPU reflection tests and five saved-MAIN audit/mutation/construction
tests pass. Mutation fixtures are temporary copies, not altered Evidence.
The existing NVIDIA native suite and11 compiled/linked program pairs pass.
The new unused TEST helper is separately linked/executed in the actual MAIN
fixture; `make check` alone would not establish that integration.

Physical model and primary Smith references remain in the sealed
[supported-transmission model](../2026-10-06-water-supported-transmission/README.md).
No copied shader-pack code, purchased assets, density/spectrum/geometry tuning
or eta-squared calibration is introduced here.

## Preserved runtime and next work

No TEST pack/Mod/config is installed this turn. Normal owned client55236 saves
all dimensions and exits0 before GL. A new post-save private baseline is made;
41 ordinary save-file hashes match before reopening without any save restore.
Normal0.6/physics0.2 and original configs/disabled TEST entries are verified.
Fresh normal runtime and paused F2 images, Java's ordinary session.lock FD and
owned launcher handle88646 are recorded in `checkpoint.json`. Iris may rewrite
its timestamp comment. Existing OpenAL failure is not repaired. No candidate
Minecraft intervals, new FPS claim or natural/motion acceptance is made.

All old Evidence/manifests and the tracked dirty-diff SHA remain unchanged.
New code/Evidence is separately named and sealed. No commit/push, subagent or
external Claude invocation occurred. The full objective is not completed.

The next implementation is a proper source adapter: actual per-direction
sky/receiver and water reflection provenance, native-Sun48 support/visibility
consistent with the diffuse operator, derivative/AA safety and explicit cave/
opaque/degenerate fallbacks. Avoid callback guesses, globally discarding good
directions, or substituting additive colors. Then validate actual source controls,
retained regressions and UUID-guarded Iris near/deep/tilt/moving views, with honest
runtime cost. Natural shore/cloud/receiver transport, coherent units/energy,
temporal contacts and the complete realism goal remain required.
