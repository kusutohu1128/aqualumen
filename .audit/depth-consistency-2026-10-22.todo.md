# Water hit depth and attenuation consistency

- [x] Reproduce it yourself on the matching surface via the driver skill (Non-negotiables), even when a debug or instrumentation protocol says to ask the user to reproduce.
  - Reuse actual hit1 near/deep point and raster records, which establish distinct optical/raster locations. Do not repeat completed TIR qualification.
- [x] Binary-search the cause. Form the candidate hypotheses, then rule them out until one survives.
  - Compare actual depth, optical point, composite distance and transmission on the same frame.
- [x] Plan the fix. If it crosses a function boundary, architect first. Delegate implementation to a subagent using your configured bug-fix model (default in poteto-mode's Models section) with a specific scope.
- [x] Verify on the same surface. The original repro now passes.
  - The unit is depth/attenuation consistency, not automatic acceptance of all visible curls.
- [x] Stage the commits so the failing repro lands before the fix in git history.
  - skip: user did not request commits; preserve dirty checkout and separate failing/passing evidence instead.
- [x] Run Opening a PR.
  - skip: no PR or publication requested.

Architect phases. Ground, Sketch, Agree, Implement, Scrap if the sketch contradicts runtime.
Arena phases. Frame, Fan out, Cross-judge, Pick, Graft, Verify.
Throughput checkpoint. Reuse hit1 inputs and source pins; gather one new same-frame depth/transport observation before expanding the experiment. Parent alone owns GPU, client lifecycle and canonical integration. Claude and Codex explore independently; writers receive isolated worktrees. Keep old Evidence immutable. Ordinary Lab0.6/physics0.2 and ordinary save remain protected.

- [x] Ground.
- [x] Sketch.
- [x] Agree.
- [x] Implement.
- [x] Scrap.
  - skip: the physical contract held; explicit nonwater diagnosis was an accepted observation-contract extension, not a discarded physical design.
- [x] Frame.
- [x] Fan out.
- [x] Cross-judge.
- [x] Pick.
- [x] Graft.
- [x] Verify.
- [x] Independent final actual Claude evidence and trail review.
  - claude-opus-5-5, both exits0, no blockers. Trail audit is sampled/capped, not the full raw conversation.
- [x] Record review flags and final handoff.
  - REVIEW-ADDENDUM.md and FOLLOW-UP.md retain all limitations. HANDOFF-SAFETY.json rechecks exact ordinary0.6/physics0.2, source/tool/archive pins and ordinary save without any new game/GPU run.

Bounded result is in reports/2026-10-22-water-hit-depth/CLOSURE.json. Full appearance/R2/general-world/physical/performance/release acceptance is not this checklist's completed claim.
