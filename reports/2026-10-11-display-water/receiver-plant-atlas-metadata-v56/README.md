# Atlas metadata v56 — actual unsized RGBA identified

Actual initial-terrain atlas rejection receipt:

`size=1024x512 format=6408 base=0 swizzle=6406 compare=0`.

The actual Minecraft atlas is unsized GL_RGBA (6408), with base level zero,
ordinary alpha swizzle and no comparison. The original readback admitted only
RGBA8/SRGB8_ALPHA8 and therefore rejected this valid alpha-bearing storage.
This metadata determines the next correction; it does not prove alpha sampling.

`candidate-receiver-probe.log` retains scoped receipts. The disposable client
was UUID-guarded quit before starting the benchmark; owned launcher exited 0.
`runtime-restored.json` verifies exact normal config/Mods and unchanged ordinary
saves without rollback. No runtime benchmark or visual acceptance is claimed.

The v57 correction explicitly admits GL_RGBA after an actual NVIDIA controlled
texture readback verifies the requested format remains 6408 and its alpha bytes
match. Other unsupported formats, base levels and swizzles remain rejected.
