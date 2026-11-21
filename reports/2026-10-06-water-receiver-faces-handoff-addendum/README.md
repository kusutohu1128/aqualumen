# Authoritative ordinary-pause correction to actual-face packet

The original45-file face packet remains immutable and its SHA256SUMS still
verifies. Its actual16-face result, installed/rebuilt producer, raw record audit,
CPU checks and before-reopening normal41-file/config/Mod exactness remain valid.
**Its claimed final pause is invalid:** `normal-pause.png` (15:34:03) is gameplay,
not a pause menu. The v1 recorder checked an arbitrary historical pause line and
accepted a supplied filename before the final image's menu state was qualified.
This addendum supersedes that paused-handoff assertion, not the face evidence.

The candidate image was caught during actual root inspection. Later15:35:08
shows creative inventory, which also does not qualify pause. No inventory item
was selected by the agent and no terrain/camera command or save rollback was
issued. View orientation changed during menu/focus interactions; no same-camera
claim is made. `windowactivate`'s active-window state did not prove X input focus;
explicit `windowfocus` established the actual focus, then inventory was closed.
Do not attribute all intervening state changes to a proved cause.

Fresh15:35:48 is root-inspected gameplay. A later Escape produces the fresh
15:36:17 normal-world `Saving and pausing game` event, and the separately viewed
15:36:17 image visibly shows the Japanese game menu. No further UI/game input
is sent after that qualified pause. The same live normal0.6/physics0.2 owned92351 /
hostJava3335948 holds ordinary lockFD154. All three normal JARs and selected pack
remain exact; all10 TEST controls absent. No native GL or timing benchmark.

A public chronology regression genuinely fails on the old saved log before the
fix, then passes: a historical pause before a later runtime image cannot qualify
the alleged pause image. A positive ordered new pause passes. The root recorder
now uses this guard before any output writes. Event chronology is necessary,
but actual image/menu inspection remains required and is not replaced by logs.

The checkpoint/new log/images and source/test output in this addendum are the
authoritative final handoff. Existing face/geometry/native/world packet files are
not edited. The full realism goal remains active; follow the face packet's
texture/radiance/source-joining next action, using this corrected live pause.
