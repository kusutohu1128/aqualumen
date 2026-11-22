Devin verified both failures in the client logs (recursive loading-screen frame; NoSuchElementException at Timers.pass:190 for an empty Iris shadow-composite slot). Both are profiler attribution bugs, Lab untouched. You are authorized to fix and continue PHASE 1.

- Make attribution total: a pass with no mapped program/compute must never throw. Name it from whatever is known (stage + index, "unnamed"), record it, and keep rendering. Any profiler exception inside a hook must be caught, counted and disable the profiler for that run (marking the run invalid) rather than crash the client. Add a failing-then-passing unit test for the empty-slot case.
- Before spending the ~5 min cold compile again, check whether the shared driver cache from the retry is usable so launches are warm.
- Then run the Phase 1 sequence with fresh labels (gp-cal-4x-c, gp-overhead-off-a, gp-p7-a, gp-p8-a, gp-p8-b, gp-p7-b, gp-overhead-off-b), same gates and constraints as before. You get up to two more diagnosed fix+retry cycles for profiler bugs in total (fresh labels each time); gate failures (calibration ratio, overhead) still stop the campaign.
- Update the report and summary with real numbers; keep the two failed attempts documented briefly.
Same final-message contents as requested before. No commit/push/prune, no Lab/dist/release changes.
