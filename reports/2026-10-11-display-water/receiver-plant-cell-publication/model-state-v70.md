# Exact model-owner state witness v70

The receiver's geometry cell identity retains block ID/kind, which cannot alone
detect property changes within the same block (for example grass snowy state).
Actual top-source mesh intake now retains the exact captured block-state string,
checks it against the loaded live owner before shading, and rereads every retained
owner during fresh phase validation. Chunk pointers are audited before and after
these rereads. Epoch/thread ownership remains guarded. Mismatches abort rather
than pair stale model radiance with an unchanged block ID.

The same witness validator is used by the bounded plant region diagnostic.
`LoadedReceiverWorld.blockState` reads only current retained loaded chunks using
the existing pinned state handle, without extra fluid/collision queries.

`../model-state-cpu-v70.log` covers coordinate identity, same-block property drift,
unavailable owner and guard expiry before/after reread. Full Mod artifact
`build/aqualumen-physics-0.3.0-model-state-witness-v77.jar` compiles and is not
installed. Existing typed geometry and run-source CPU regressions pass. Actual
in-game property-change/unload testing remains open; v69 runtime used the previous
artifact and cannot be cited as validation of this correction.

The v69 underwater-up-near PNG was visually inspected this turn. It is an explicit
diagnostic palette image (large dark center, green/gray exterior), not a natural
render. Therefore it cannot establish the natural underwater sky appearance or
Sun acceptance. No ordinary-play settings or saves were changed this turn.
Full world-model coverage, live plant traversal/shading, acceptable temporal
performance and the complete water/sky/Sun goal remain unachieved.
