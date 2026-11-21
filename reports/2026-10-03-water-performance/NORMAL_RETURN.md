# Read-only normal handoff check

2026-10-03, after normal relaunch. Root inspected the fresh paused return
image; an independent read-only agent checked the following current filesystem
state without changing files, operating game/processes or running GL.

- Selected `Aqualumen-0.6.0.zip`, SHA-256
  `6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`.
- Active physics0.2.0, SHA-256
  `1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e`.
- Only Iris, Sodium and physics0.2 JARs enabled. TEST JARs recoverably disabled.
- Benchmark/Sun TEST opt-ins, observer requests and benchmark
  `request.properties`/`command.properties` absent.
- `pauseOnLostFocus=true`, maxFPS120, VSync off,1600x900,
  renderDistance12, simulationDistance6.
- Every non-comment Iris config value equals the private preturn copy.
  Do not claim its postlaunch timestamp comment is byte-identical.
- Root `git diff --check`: exit0. Old1358-entry Sun-support packet
  `sha256sum --quiet -c SHA256SUMS`: exit0. Both root final profile audits
  byte-equal to independent archived outputs. Root4 profiler build tests and
  5 prepared CPU tests PASS; corresponding root logs are archived here.

This check is a current handoff snapshot, not a historic every-run installation
receipt. Private launcher/account logs and the comparison-only ordinary save
copy were not published. No ordinary save restoration was performed.

Owned normal session43713 remains live and paused, as shown by
`ordinary-return-paused.png` (fresh19:32:21). Unpause via the game menu to play.
GPU/native follow-up must first save/quit that same client and check Java absent.
