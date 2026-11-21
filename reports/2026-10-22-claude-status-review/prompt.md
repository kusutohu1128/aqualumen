# Independent Aqualumen status investigation

The user asks: "Claudeに現状の調査もさせてください".

You are Claude, independently investigating the CURRENT repository /home/kusutohu/repos/aqualumen. The implementation goal is PAUSED. This request is read-only investigation, not permission to fix, install, run the game, benchmark, or resume implementation.

Only Read, Glob and Grep tools are available. Do not spawn agents, write any file, issue commands, access credentials or auth logs, contact external services through tools, or change existing Evidence. Produce the complete report as your final response; the parent saves it. Do not claim a test or runtime check was executed by you.

Read AGENTS.md first. Then use these entry points, verifying their claims against current code and actual saved runtime metadata rather than accepting the documents uncritically:

- docs/REALISM_GOAL.md and docs/DISPLAY_WATER_GOAL.md. Distinguish full water/sunlight/useful-physics goal from a diagnostic checkpoint.
- docs/RECEIVER_FIELD.md. Its opening and later sections may reflect different checkpoints.
- reports/2026-10-11-display-water/receiver-plant-owner-halo-v100/candidate-runtime-inputs.json, candidate-runtime/complete.json, candidate-runtime/underwater-up-near.json, candidate-runtime/underwater-up-moving.json, candidate-receiver-runtime.log, runtime-restored.json, candidate-launcher-exit.json.
- Read the latest candidate PNG reports/2026-10-11-display-water/receiver-plant-owner-halo-v100/candidate-runtime/underwater-up-near.png if your Read tool supports images. State whether you actually saw it. Optionally inspect one moving frame; do not infer motion quality from one still.
- reports/2026-10-11-display-water/underwater-coupled-beauty-v92/README.md and docs/reviews/underwater-reflection-hemisphere-2026-10-11.md for rejected/nonaccepted visual experiments.
- Current shaders/lib/water.glsl, shaders/lib/water_receiver.glsl and relevant plant material/shading files, plus current physics-mod/dev/aqualumen/physics classes that actually publish world-source and plant owner/material data. Discover the exact current files and runtime entry points with Glob/Grep. Do not exhaustively enumerate every old report.

The parent's previous status claims, which you should challenge where evidence warrants:

1. Experimental world-material/light-to-water-reflection flow has real Minecraft evidence through candidate v100, but visual realism remains unaccepted.
2. Folded/compressed underwater sky-window boundaries and a broad dark exterior remain visible. Do not call every circular underwater sky window a bug; distinguish legitimate Snell/TIR effects from demonstrated artifacts.
3. Saved v100 near/moving runs show mean FPS about 2, but these are instrumented 1600x800 runs with image capture and source producer work. They do not establish clean ordinary-play FPS or prove capture is the bottleneck.
4. Normal Lab settings in the last status inspection selected 0.6/physics0.2; saved runtime restoration metadata said configs/Mods/ordinary save exact, no rollback. Your restricted tools cannot verify current host processes or current installed config outside the repository. Treat the current host state as unverified by you.

Deliver Japanese report, approximately 1000-1800 Japanese words/characters as needed for a useful diagnosis, with concise sections adapted from Overview / Key concepts / How it works / Where things live / Gotchas. Address:

- What is actually implemented, runtime-proven, only fixture-proven, opt-in, rejected, or still missing? Separate current source from the pack that was actually tested and from ordinary installed releases.
- The 2-4 most important remaining defects or risks. Cite exact file:line and symbols for code claims, actual JSON fields/log lines for saved observations. Mark every inferred cause as a hypothesis, not a verified root cause.
- Trace the actual source collection, shading, publication, water draw path sufficiently to identify the next leverage point. Explain the material/lighting/geometry ownership and readiness boundaries without assuming archived fixtures prove live ownership.
- Does performance evidence identify a limiter? Look for actual producer collection/shading/validation/packing timing fields in saved logs; if no clean profile exists, say what is missing. Do not claim speedups or causal comparisons from unlike runs.
- Recommend the next bounded causal experiment most likely to improve the user's visible underwater problem, with a rejection criterion. Recommend only; execute nothing.
- Correct any inaccuracies in the parent's status. Finish with a short plain-Japanese summary suitable for the user.

Use only evidence you actually read. Images and reports are observations from their recorded date, not a new October22 runtime. The report must not declare the full goal complete.
