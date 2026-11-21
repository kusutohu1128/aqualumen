# Real coast world-space rays and independent first-cube/camera occlusion

2026-10-06 JST. Concrete diagnostic progress toward natural water appearance,
not a production visual fix or completed realism goal. Original production
shader hashes are unchanged. Earlier phase0/45, geometry roles and9->32 budget
experiments were not rerun. All prior sealed packets/releases are retained.

## Finding that changes the implementation path

The original MAIN's actual `absolutePosition` and `transmitted` are exported
at the same invocation as the solver stop and last source position. Sixteen
previously selected dark/bright points have actual known-water producer masks,
seven distinct RGBA32F sampler roles, finite records and restored observer state.
Request `c6eb1f71-4a0a-4492-a7b2-4c535c5ccff1`, frame3846, exact guarded V2 world.
These are world rays, not view rays inverted using guessed matrices/player pose.

An independent bounded reader decodes saved Anvil sections/palettes/padded packed
indices for Minecraft1.21.1/DataVersion3955. It traverses the physical refracted
ray through air/water to the first declared supported full cube. All16 selected
first receivers are sand. Unknown/noncube/cutout blocks and edge ties return
unsupported; reader controls prove they are not silently ignored or filled in.

For **every one of the eight dark points**, the physical first sand receiver is
occluded along the straight camera ray by a different nearer sand cube. The
blocking cube is0.6516–3.2609m before the target. For **all eight bright controls**,
the camera ray reaches the same first sand receiver. Refracted and camera-ray
traversal block states agree between two separately saved closed TEST snapshots.

The successful shader paths differ from physical first-cube distance by less
than0.0081m; last sampled source point is0.00053–0.00862m from that first point.
Dark paths are the existing proxy, not independently proved physical first
distances; last candidate/source points differ by0.05784–3.2280m from physical
first points. These descriptive differences are not a fitted acceptance gate.

Combined with the preceding negative9->32 budget experiment, this strongly
supports camera-depth source absence/occlusion for these selected bands rather
than simply insufficient iteration count. A physically present refracted floor
need not be visible in a straight camera depth buffer. Do not force hidden
receivers through screen-space guards or recolor a wrong source to hide a band.
The [next implementation direction](../../docs/reviews/codex-occluded-water-receiver-next.md)
is a conservative actual world geometry/material/light receiver path through the
read-only client bridge, preserving the screen path and closed-bank protections.

## Scope and honest limits

- Point-center visibility within the explicitly supported full-cube subset is
  qualified. Finite rendered depth pixel footprints, universal shoreline cause,
  arbitrary shapes/materials, frozen same-frame world geometry and full physical
  water-membership/source transport are not proved. Geometry matches across
  saved snapshots, not a GPU/CPU world snapshot from the raw frame.
- Existing wave/source laws, geometry, trace guards/tolerances and iteration9
  remain unchanged. No extra trace or depth texture lookup; exact source recovery
  passes. Extra diagnostic world arithmetic does not prove GPU C0 neutrality.
- Actual Iris1.8.8/RTX3080Ti coast run at2560x1440/render12/simulation6:248 positive
  raw intervals, mean49.798FPS, P99 23.163ms, worst23.235ms, focused capture,
  shader active/no fallback. This five-second diagnostic atlas workload is not
  production performance, an exact timing A/B or a general FPS guarantee.
- TEST pack SHA256 `ab580bc7f722acd50d25147cfa57716d6b6372dde009d1347fa4d714350ef964`.
  Original strict reporter accepts the actual saved run. Native11 pairs+3 compute
  entrypoints compile/link on NVIDIA GL4.6; no native dispatch/draw/readback or
  regression acceptance is claimed from compile-only. Iris executes separately
  with its recorded GL3.2 context. Root inspects the actual atlas; strong cyan and
  serrated dark bands remain. PNG and raw are different frames.
- FINAL model-view inverse is active in the saved raw; projection inverse and
  cameraPosition uniforms are inactive. Do not fabricate their values. This
  reader uses actual MAIN world fields and the observer's unshifted camera for
  independent 3D point/cube visibility, not a projection-footprint reconstruction.

## Failures preserved, safety restored

The initial ordinary UI/window-close attempt lacked a clean-save exit and left
only an owned stranded launcher after Java/window disappearance. Its exact
launcher was terminated after read-only identity/absence checks; exit143 is not
called clean. Normal0.6/physics0.2 was reopened without any TEST install or save
replacement. Inspected keyboard Save/Quit and titleQuit then complete with all
dimensions saved and recovery launcher18279 exit0. Only then was the fresh41-file
post-save ordinary baseline made. `PLAN.md`/interruption log retain the failure.

A shared lifecycle import briefly misrouted an exclusively NEW witness JSON into
the old stop report. No sealed file was overwritten; the positively identified
new file was moved without overwrite into this report and the side-effecting
import removed. The old stop seal passes and the extra file is absent. This
routing failure is retained in the plan; it is not hidden as a successful path.

The actual TEST13904/Java3290953 exits0, all dimensions saved. Normal configs/
three JARs and41 ordinary saved files match fresh baseline before reopening.
Nine TEST entrypoints are disabled recoverably, physics0.2 restored; no save
restore or ordinary camera/time/terrain benchmark automation. A fresh ordinary
runtime/pause handoff is checked in `checkpoint.json`. Saves naturally resume
after launch, so no frozen postlaunch-save claim. No native GL after final normal
reopening. All earlier seals and this NEW seal are checked.

Final ordinary owned59228/Java3294081/lockFD154 is qualified live; root inspects
runtime14:45:21 and pause14:46:18. Thirteen CPU source/reader/import-chain checks
and diff whitespace check pass. An isolated previous import-chain RED versus
the current pure predicate import GREEN guards against the observed misrouting.

Production is not changed from these diagnostics. Natural coast/motion/contact
appearance, coherent Sun/Moon/cloud/volume transport and honest useful physical
effects remain required by the full realism goal, which stays active/unachieved.
