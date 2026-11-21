# Alpha v55 — real atlas storage rejected, not runtime acceptance

Added bounded immutable base-level atlas alpha storage, nearest/linear CPU
sampling with repeat/clamp addressing, and GL readback which restores texture
binding, pixel-pack buffer and pixel-pack layout. Synthetic CPU and NVIDIA GL
tests pass. Actual Lab initial-terrain capture rejected the real atlas as
unsupported storage; no alpha model samples were obtained in this checkpoint.

The receiver probe log is `candidate-receiver-probe.log`. The disposable client
was UUID-guarded quit before starting the static/moving benchmark and its owned
launcher exited 0. There is no completed benchmark or visual acceptance claim.
`runtime-restored.json` verifies exact normal config/Mods and unchanged ordinary
saves without rollback. v56 adds storage metadata to identify the rejection
instead of guessing or treating unavailable alpha as transparent water.
