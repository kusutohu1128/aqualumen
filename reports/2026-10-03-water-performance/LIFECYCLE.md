# Observed lifecycle

Only root operates Minecraft/GPU. Times are Asia/Tokyo on2026-10-03.

- Owned normal session96154 was live and paused. Fresh18:43:08 F2 image was
  inspected (`ordinary-start-paused.png`). Grounded SaveQuit18:43:40 saved
  players/worlds/all dimensions; fresh18:43:52 title image was inspected
  (`ordinary-saved-title.png`). Grounded title Quit finished the SAME session
  with exit0. Java absent before the first TEST launch.
- Whole ordinary save copied AFTER clean exit to a private comparison-only
  directory. No save restoration. No ordinary camera/time/terrain automation.
  Original options/Iris/inactive benchmark configs privately copied.
- Original baseline TEST session47628 selected the exact frozen zero-physical
  ZIP, benchmark.3.9/Sun.1/physics.3/stage.1. Three-view run
  `water-perf-baseline-20261003-1847` completed18:47:45;10s warmup+10s sample
  each,900p/off/120cap/render12sim6. No observer requests. Guarded quit finished
  SAME session with exit0; Java absent before replacing TEST JARs.
- Instrumented TEST session35654 launched with the new pinned pair-v1 JARs,
  same IDs/versions and unchanged shader ZIP. `sun_profile=control` disables
  only measurement clocks/counters, not permission checks or ZIP read/hash.
  Original JARs were moved to new recoverable `.performance-baseline-closed`
  names; normal physics.2 remains recoverably disabled during TEST clients.

Private launcher account output is excluded. Startup SoundSystem/OpenAL error
also recurred; it is separate from shader correctness and not fixed here.
Subsequent TEST clients, all owned by root and serialized:

- Control1 session35654 completed `water-perf-control-20261003-1908`
  at19:09:47. Profile1 session8834 completed
  `water-perf-profile-20261003-1913` at19:14:29.
- Profile2 session15702 completed `water-perf-profile-repeat-20261003-1918`
  at19:19:59. Control2 session32463 completed
  `water-perf-control-repeat-20261003-1923` at19:24:26.
- Each measured near/deep/tilt with10s warmup+10s sample, the same frozen ZIP,
  exact disposable V2 UUID, settings and shader phase. Observer requests were
  absent during sampling. Only the first pair has actual scalar guard int1
  captures AFTER completion; those requests were then closed recoverably.
- Each client was guarded-quit through its SAME owned session, returned exit0,
  and Java absence was checked before the next launch. All telemetry collectors
  ended. No concurrent native GL experiment was run.

Normal restoration and handoff:

- TEST JARs/opt-ins/requests disabled recoverably; no material deletion.
  Selected normal0.6 ZIP and active physics0.2 JAR hashes rechecked. Original
  options, Iris and inactive benchmark config restored from private preturn
  copies; options cap120/VSync off/1600x900/render12/sim6 and
  pauseOnLostFocus=true. TEST's temporary pauseOnLostFocus=false not retained.
- Before ordinary relaunch, recursive ordinary-save comparison against the
  after-clean-save private copy returned0. No save restoration. Subsequent
  ordinary-world advancement is natural play/launch, not TEST automation.
- Normal owned session43713 launched at19:29:30. Fresh log selected
  Aqualumen-0.6.0.zip at19:29:41, created overworld pipeline at19:29:45, and
  initialized physics0.2 at19:29:47. Iris can rewrite its comment timestamp on
  launch; config values, not a postlaunch byte-identical claim, define handoff.
- Fresh ordinary in-game F2 image19:31:11 inspected without moving the camera.
  Grounded Escape19:31:20 paused the game. Fresh19:32:21 F2 image inspected:
  actual game menu over the ordinary shore/ocean. Archived as
  `ordinary-return-paused.png`, SHA-256
  `66fc971c321350bacb81fba25f0a7d5241be1a11c48e14a8c31208e0034f8876`.
- Session43713 remains live and paused. Any future native GPU work must first
  save/quit THIS owned normal client and verify Java absent. Private launcher
  output and save copy remain private; do not restore that comparison copy.

Root replayed both final independent readers byte-identical to archived
outputs, reran4 profiler build tests and5 prepared CPU tests (all PASS).
Only this new packet is sealed; the prior1358-entry Sun-support packet remains
untouched and was separately hash-checked successfully during this turn.
