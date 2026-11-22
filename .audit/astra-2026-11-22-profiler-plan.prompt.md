New task from the user, via Devin (observer). Same rules as before: follow AGENTS.md, Devin reviews and makes all git commits, no push/prune, Lab stays at 1.8.0 with compiler disabled, one GPU job at a time after checking nvidia-smi/ps.

## Goal
The user asked why Aqualumen is so heavy. Devin's evidence-based answer (no profiler available; nsys/ncu/Nsight/RenderDoc are not installed):
- 1.0 sky-looking view 283 FPS vs ground views 69-85 FPS at 1440p => view-independent per-frame work (shadow capture + compute + VirtualGL path) was <= ~3.5 ms in 1.0; the rest is per-pixel shading of visible terrain.
- Per-lamp per-pixel shadow rays: 1.5->1.6 door room two lamps 61.1->44.8 FPS (+5.9 ms) while lamps-off was unchanged; 1.8.0 birch lamp off->one torch 49.6->31.3 FPS (+11.8 ms).
- Preview 3 (lava area lights) made the lava-free birch lamp-off view 44.3->33.0 FPS (+7.7 ms). Hypothesis (unproven): the uber terrain/deferred shader's register pressure lowers occupancy; supporting signs are the NVIDIA inline pragma compiler mod and ~4 min cold compile.
- Every-frame full recompute passes (canopy prepare2, ground prepare3/4, bounce shadowcomp2/3/4): preview 7's second bounce cost +3.4 ms at night.

The user approved building our own in-game GPU profiler so these attributions are measured, not inferred.

## Your task now: PLAN ONLY
Do not edit tracked files, build, or launch anything in this turn. Read what you need. Write `.audit/astra-2026-11-22-profiler-plan.md` (only file you may create), under ~140 lines, covering:

1. Design of a client-only Fabric profiler mod pinned to Minecraft 1.21.1 / Iris 1.8.8 / Sodium 0.6.9, placed with the existing tools (e.g. a new `tools/gpu-profiler-mod/` + build script, or an extension of the existing frame observer used by reports/2026-11-21-animal-light/run.py — justify). Use GL timer queries (GL_TIMESTAMP via glQueryCounter, or GL_TIME_ELAPSED without nesting), a ring of query objects read back N frames later with no CPU stall, and restored GL state. List the exact Iris/Sodium classes and methods you will hook (verify against the installed pinned jars, e.g. net.irisshaders.iris.pipeline.CompositeRenderer / IrisRenderingPipeline / ShadowRenderer / FinalPassRenderer and Sodium's chunk render passes) and the resulting named ranges: shadow terrain/entities, each shadowcomp/prepare/begin/deferred/composite pass by program name, gbuffers terrain solid/cutout/translucent, entities, hand, water, final, plus a whole-frame GPU range. State what cannot be separated.
2. Safety: enabled only for the private benchmark clients the existing runner creates (same UUID/marker guard pattern as the frame observer), never in Lab; output CSV per frame + summary JSON into the run directory.
3. Validation of the profiler itself: CPU unit tests for parsing/aggregation (red -> green); a GPU sanity check that a known pass's range scales as expected (e.g. a glcheck-style synthetic or toggling LOCAL_BOUNCE / LOCAL_LIGHT_SAMPLES changes the expected range and not others); sum of ranges vs whole-frame GPU time; profiler overhead measured as frame-interval difference with the profiler on vs off in the same scene (state a tolerance).
4. Measurement campaign using the existing ABBA scenes (both-west night two lamps, day-white noon) on preview 7 and preview 8, and on 1.8.0 to test the preview-3 regression hypothesis if the scenes are valid for 1.8.0 (check). Optionally a sky-looking control. Exact run labels and commands. Report per-range median and p95 ms.
5. Deliverables: report directory (e.g. reports/2026-11-22-gpu-profile/README.md in the project's Japanese report style), what will be committed vs left ignored.
6. Note whether NVIDIA program binaries (glGetProgramBinary) could expose register counts for the occupancy hypothesis — propose a quick read-only feasibility probe, but mark it optional and unverified.
7. Risks and stop conditions.

End your final message with the plan path.
