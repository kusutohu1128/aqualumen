I made about 14 read-only file reads within the allowed budget. I ran no commands. Nothing here is runtime verification.

**No blocking findings.** I found nothing new that shows the generation3 witness is invalid or circular, and I'm not reopening the rejected join with the old 445 coordinates.

## What I checked

- **The marker is independent of the error being measured.** The marker comes only from patched nonwater fragment shaders (`tools/water_hit_depth_ownership.py:129-137`). It is not chosen by looking at depth or distance error. Every pixel classified as water still uses the original budgets: 1 mm distance, one D24 depth step and 1e-6 Beer (`tools/water_hit_depth_audit.py:89-103`). A nonwater program without the marker that wrote depth over water would leave a stale water record. That pixel would then fail, not be hidden. The marker checks are strict: exact all-zero C12, exact zero C3 xyz, and no overlap with water (`water_hit_depth_audit.py:110-112`).
- **Water's own blend state did not change in generation3.** This was my main suspicion. The base properties set blending for the whole `gbuffers_water` program (`shaders/shaders.properties:17`), and the new key list includes `gbuffers_water`/`hand_water`. However:
  - The generator only appends keys that are missing, and it raises an error if an existing key is not `off` (`water_hit_depth_ownership.py:141-145`).
  - A test shows that appending `blend.gbuffers_water.colortex12=off` to the generation2 pack raises a duplicate-key error. So the key is already there (`tools/test_water_hit_depth_ownership.py:82-86`), and all existing keys keep their values (`:67-68`).
  - The optical probe already sets water C3 blending to off (`tools/water_optical_probe.py:16-19,94`).
  - Only the two patched shader files and the properties file can change (`water_hit_depth_ownership.py:176-178`).
- **The native test covers the opaque terrain path too.** `gbuffers_terrain.fsh` and `gbuffers_textured_lit.fsh` have the same pinned hash (`CLOSURE.json:33,37`). So the textured_lit native test compiles the same bytes that opaque terrain uses.
- **The saved numbers agree with each other.**
  - 1439370 + 630 = 1440000, and 1439567 + 433 = 1440000.
  - `visibleWaterChangedPixels` = 1063 = 433 + 630. This means the baseline3 and candidate3 marker sets share no pixels at all. That fits live particles, and it further supports rejecting a same-pixel join with old frames.
  - Mutual pixels: 1440000 − 1063 = 1438937.
  - The maximum candidate deep error is 5.02e-5 m, and the farthest accepted point is 5.50 m. Both match `SUMMARY.md:14,16`.
- **The native overlay test is meaningful.** It requires more than 100 markers and zero markers in the old program, the same C0 and depth with and without the diagnostic, and depth changes that match the depth mask (`tools/water_hit_depth_ownership_native.cpp:86-91`). It also requires the blend-on, discard and occlusion controls to behave as expected (`:97-102`).

## Minor, non-blocking issues

1. **Low: the generation3 audit doesn't enforce two things it reports.** `declaredCheckPassed` does not require `nonwaterWithoutExactMarkerPixels == 0` or a nonzero marker count (`water_hit_depth_audit.py:102-118`). The "zero unmarked nonwater" statement is backed by the saved value (`candidate-deep-owned-audit.json:114`), not by a pass condition. This doesn't weaken the water claim, because unmarked nonwater pixels are never part of the water check. But a future run with a gap in markers would still pass. Suggestion: describe it as observed, or add it as a pass condition before any rerun.
2. **Informational: `stale_old` is printed, not counted.** The overlay output prints `stale_old=<count>` (`water_hit_depth_ownership_native.cpp:95`). The real check is that every pixel stayed water in the old program (`:89`), which is stronger. The printed number just repeats the marker count. The wording is cosmetic, and the SUMMARY doesn't rely on that field.
3. **Informational: one manifest field is hard-coded.** `waterVertexCompositeBytesExact: True` is a literal (`water_hit_depth_ownership.py:203`). The fact itself is enforced by the changed-file check at `:176-178`, so the field is accurate, but it isn't measured on its own.
4. **Informational: naming.** `historicalGeneration2CandidateWrapperExitCodeObserved: false` (`CLOSURE.json:156`) is consistent with keeping the wrapper's 143 on record and not calling it exit 0. A reader could still take "observed" to mean the 143 was never seen. A short pointer to `LAUNCHER-EXIT-ADDENDUM.md` would remove that ambiguity.

## Accepted limitations (correctly left open, no action needed)

- The marker means "last known nonwater diagnostic writer". It does not mean depth or beauty ownership. Depth-mask-false overlays legitimately mark pixels without changing depth.
- Blending is configured off for all 27 program IDs, but Iris's fallback source resolution was not observed. The exact −3 values in the actual captures only show that blending was off for the programs that actually drew here.
- The native fixture sets blend state directly, not by parsing Iris properties. The reclaim control is a synthetic shader, not the real water program.
- Not covered: `gbuffers_basic`, `skybasic`, `line`, and the nonwater branch of the water program; arbitrary packs and dimensions; and depth-stencil sampling with its fallbacks.
- No actual matrices were captured. The eye-relative origin is checked only through the baseline raster chain, to 1 mm. Actual water draw state, actual opaque straddles and ceilings were not observed. There is no proof that the C0 of the instrumented and uninstrumented whole scenes match.
- The scope is the frozen 17 s scene, zero ripples, known deep water and a points up to about 5.5 m away. No claim about general distances or worlds.
- The timings (1.90/2.36 FPS) are single instrumented runs. There is no profiling or interleaved repeat, so there is no speedup or regression verdict and no production FPS number.
- Full visual, physical, R2, dynamic, general-world, performance and release gates remain open.

`CLOSURE.json` and `SUMMARY.md` state these accurately. This finishes only this bounded unit (hit, depth and eye attenuation plus the known-nonwater writer protocol). It does not finish the curls or the release.
