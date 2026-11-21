# Next action: implement conservative occluded receiver support

Check the normal checkpoint's actual handle/PID/current ordinary lock before any
new cycle. Normal0.6/physics0.2 is restored and paused; do not use old TEST config.
Full water/sunlight realism goal remains active. No commit/push/remote model call.

Completed: actual16 MAIN world-space rays, same invocation last source/stop,
independent saved first-cube and camera-ray traversal, stable visited block states
across closed snapshots. All eight dark physical receivers are occluded by nearer
sand along camera rays; all eight adjacent positives are camera-visible. Do not
repeat phase0/45, role pairs,9->32 or these diagnostics without regression cause.

Read `docs/reviews/codex-occluded-water-receiver-next.md` (frozen copy in packet)
and implement its first deliverable: failing genuine production-MAIN occluded-
first-receiver regression, pure bounded receiver snapshot/traversal contract,
then conservative world geometry/material/light-source support in the client
bridge. Cross-check the16 actual rays, preserve the near FIRST vs BACKGROUND
negative, unknown/noncube handling, original source laws and all optical guards.
Do not assume the smooth bathymetry depth/validity map includes occupancy/albedo/
normal/radiance, or simply use a constant sand color/wrong visible source.

Finite source pixel footprints and arbitrary geometry remain unqualified; the
point-center solid-cube evidence does not establish full rendering correctness.
Keep native math/GL, actual Iris sampler allocation and Minecraft timings/visuals
separate. Camera/contact motion and coherent Sun/Moon/cloud/volume remain full
requirements; this shore architecture slice is not a replacement for that goal.

Next authorized Lab TEST needs a fresh clean normal post-save baseline, exact UUID
guard/opt-in, separate NEW artifact paths, serialization with native GL, clean
TEST exit and reversible normal restoration. Never restore ordinary save copies.
Old seals and these tools/report are immutable; use NEW writers for follow-up.

Import caveat: prior raw readers import lifecycle modules with process-local OUT
side effects. Do not import them for a tiny pure validation predicate: the world
raw reader now owns its pure known-water check. Initial routing/UI failures are
retained in PLAN/README; neither is a successful clean/physical validation.
