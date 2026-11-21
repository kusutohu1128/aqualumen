# Timing reader v2

This is the bounded follow-up to the preserved `HANDOFF.json` and v1 source/test snapshots.

The only change is an exact fixed `(framebuffer, VAO)` reference across **all** chronological rows, for all six fixtures and both variants. Every row still passes the existing typed integer and draw-state checks before this comparison. Updating the state hash does not make a changed one-row FBO/VAO valid.

The new public mutation test was first RED for both fields against v1, then GREEN after the five-line check. Five public tests / 22 mutation negatives now pass; scoped diff check passes. All are synthetic CPU evidence, no GL and no actual timer output audited during implementation.

Use unchanged API/CLI from the original README. All timing formulas, ABBA/warmup/measured policy, source/input identity checks and scope restrictions are unchanged. Detailed storage/type proof remains with the independent main reader. No FPS, universal speedup or physical/visual/shipping acceptance is inferred.
