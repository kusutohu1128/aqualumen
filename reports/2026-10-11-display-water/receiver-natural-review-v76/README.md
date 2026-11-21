# Natural-render review v76 — unsupported scene request, stopped and restored

This run uses the current uninstrumented shader ZIP, not the unknown-kind palette:
`Aqualumen-DisplayWater-NaturalReview-v76-2026-10-11.zip`. Physics Mod v82 SHA256 is
66145213584cfe601fb7dda3974395bfae468c7fd39da8f2851003ef6987c4e8.
The plant backend is still disabled in ordinary programs; this run does not claim
plant traversal adoption. It does exercise the current exact model-state source
witness checks in the real source producer.

The reversible UUID-guarded Lab requested ocean-sun-day, ocean-sun-dusk,
underwater-up-near and underwater-up-moving, warmup 5 s/sample 10 s, auto quit.
Initial source publication frame 3/resources 1 succeeds with 55983 records,
6748 sources, ready=2 and unknownKinds=false. This establishes static current-owner
compatibility, not actual mutation/unload acceptance.

The first two start attempts were rejected before any request: no live Java yet,
then no fresh singleplayer world pipeline. The same owned launcher remained live;
after the current pipeline was observed a single measurement request was sent.
No restart or prior-run overwrite occurred. Packet-routing CPU tests distinguish
the new v76 output/artifacts/scenes from the retained v69 region packet; all 18
runtime/diagnostic-builder tests pass.

Native evidence is compile/link only, explicitly not rendering/visual acceptance.
The measurement request was rejected as unknown/duplicate scenarios: this packet
inherited the projection-guard benchmark, which lacks the dedicated ocean-sun
scenes. No natural review images or complete run were produced. The exact-world
quit request ended the same owned launcher with exit 0, without restart.
`runtime-restored.json` confirms exact normal config/Mods and unchanged ordinary
save, no save rollback and unchanged instance config. The dedicated Sun-view
benchmark artifact exists with its retained known hash; a new unique packet must
use it instead of reusing/overwriting this failed request's evidence.

Sun size/glare, underwater sky rim, temporal appearance and runtime timings remain
unverified by v76. Full water/sky/Sun completion is not claimed.
