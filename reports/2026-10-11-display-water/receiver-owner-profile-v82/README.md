# Actual receiver CPU profile v82

Owned NVIDIA/Iris run `display-water-candidate-20261011-v82`, request
`09cf4570-e090-4486-aa4a-e636c4a87ec7`, completed with automatic quit and launcher
exit zero. Runtime artifacts are in `candidate-runtime`. Normal config/Mods
and instance settings were restored exactly; ordinary save unchanged, no
save rollback. See `runtime-restored.json`.

The corrected cwd-relative JFR recording started explicitly and produced a
finalized 1,609,005-byte file. Raw JFR is retained in the private game-directory
path recorded by `candidate-profile-start.json`, directory mode 0700 / file
mode 0600. Only aggregate class/method counts are public in
`cpu-sample-summary.json`; raw recording may contain environment information.

JDK `jfr print --json --events jdk.ExecutionSample` exported 733 execution
samples, of which 688 belong to Render thread. 505 Render-thread stacks contain
receiver code. Nearest receiver frames include `LoadedReceiverWorld.receiverCell`
(132), `ReceiverRunSourceCapture.capture` (67), `lightingCurrent` (63),
`Contacts.ensureUpdate` (31), and `Contacts.update` (14). These are sampled
Java execution counts, not exclusive durations, percentages of frame wall time
or GPU attribution. Profiling overlaps benchmark execution, so its timings
are not clean uninstrumented A/B acceptance evidence.

The profile establishes that both fresh cell observation/classification and
per-read ownership checks deserve targeted optimization. It does not justify
skipping validation, caching old-frame lighting, or fabricating reflected
receiver coverage. The first narrow follow-up moves `System.nanoTime()` after
Contacts' unchanged-frame/failed-state early return. All frame/pack/world and
resource checks remain in place. Reduced actual frame time is still unmeasured.

Water-window/folded-rim, reflected geometry, Sun and coherent illumination
requirements remain open. Obtaining this profile is not completion.
