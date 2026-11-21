# Iris-owned receiver lighting pass

`prepare1.fsh` now executes the shared receiver lighting stage after the sky/clear
cache pass. Total and direct-Sun radiance have distinct 16x256 RGBA32F C10/C11
targets. The source used by the native draw test is the actual root prepare1
fragment shader. `../native-prepare-source-targeted.log` qualifies independent
tinted material/block-light/direct-Sun RGB, rain/shadow/skylight gates and invalid
inputs in the native fixture; `../native-prepare-source-full.log` records the
NVIDIA full regression and 14 linked root program pairs.

Actual Lab evidence in `source-runtime.log`:

- Program.use tail: frame 1, program 19, input size 0x0, bound FBO 12.
- Total attachment 66, direct attachment 68: both 16x256/internal format 34836
  (GL_RGBA32F). These are binding/storage receipts, not pixel readbacks.
- At frame 1 the source light direction was undefined and was rejected; the
  source input was already unavailable, not a manufactured ready material.
- At frame 2, source program 19 yielded qualified same-size distinct sky/clear
  bindings, comparison shadow binding and finite lighting values.

Actual NVIDIA/Iris near-upward view completed without fallback; native sequence
audit verifies 33 PNGs. Source input size remains explicitly zero, with unavailable
input samplers assigned distinct units by Iris. This is not positive natural
source publication, Sodium AO/filter ownership, C10/C11 RGB readback, reload or
moving-camera radiance coherence. It does not fix the dark exterior/rim by itself.
Those full-goal requirements remain open; do not replace unsupported sources with
guessed seabed or air sky.

Experimental Mod SHA256:
`28e4e04daafb9e728b9804d590a01e132492214c704d6ba42237ccdc768a0c9c`.
The client exited normally and `runtime-restored.json` verifies exact normal
configuration/mods and unchanged ordinary-save bytes without rolling back saves.
