Devin (observer) reviewed .audit/astra-2026-11-22-plan.md and APPROVES option A with these changes:

1. Implement everything in the plan up to and including the four ABBA Minecraft timing runs (eye-frames-p7-a, eye-frames-p8-a, eye-frames-p8-b, eye-frames-p7-b, plus the -c pair only if your stated rule triggers), R/frame_times.py, R/test_frame_times.py (red -> green as planned), the measure.py staged-path change, the correctness probes (make check-eye, --play-release on the unpacked 8, Mesa --eye-exposure-probe), R/frame-times.json, and a new results section in reports/2026-11-22-eye-adaptation/README.md.
2. STOP before publication. Do NOT copy anything to dist/ or to the Lab instance, do NOT write R/lab.json, and do NOT edit the top-level README.md or docs/REALISM_GOAL.md. I will approve publication separately after reading the numbers.
3. Note: an earlier interrupted attempt left only a "eye-cost: 描画ロック待ち" line in reports/2026-11-21-animal-light/progress.txt with no output directory; ignore it and do not reuse that label.
4. Before every GPU job check nvidia-smi and ps exactly as your plan says; one GPU job at a time. If a run fails, keep its receipt, do not patch shaders, retry at most once with a fresh label, then stop and report.
5. Do not git commit, push, prune or change git config. Do not touch any other Minecraft instance.

Final message: list every file you changed or created (tracked and untracked), test output summary (red then green), probe results with renderer strings, per-run and paired 8-7 FPS / mean interval / p99 per scene (both-west, day-white), cache status and launch-to-first-render times, whether any threshold was crossed, and confirmation that Lab files are unchanged.
