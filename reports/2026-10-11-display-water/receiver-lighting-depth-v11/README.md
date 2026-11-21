# Actual Iris lighting intake

The corrected adapter returned a qualified lighting capture at frame 2/resource
generation 1/program 300, after Iris's ExtendedShader sampler/common/custom
uniform and image updates. The successful receipt is `lighting-runtime.log`:

- Sky: unit 3, texture 58, sampler 0, 1024x512.
- Separate clear-air cache: unit 4, texture 60, sampler 0, 1024x512.
- Shadow: unit 5, texture 67, comparison sampler 2, 2048x2048.
- Camera `[448.5, 62.386974, -383.5]`, view-space Sun
  `[0.0, 0.0, -99.999985]`, rain 0, cloud time 0.203.

The missing-uniform rejections from programs 210/216 remain expected candidate
selection evidence; they did not qualify lighting. Uniform matrices are captured
as finite owned values but are not independently reconstructed from this view.
One bounded first-success log is emitted per registration generation; it is not
a log of every frame or a resource-reload acceptance test.

The actual NVIDIA/Iris near-upward scene completed without fallback. Native audit
verified 33 source PNGs. The final near screenshot was visually reviewed: the
dark exterior and stretched/distorted rim remain. This change does not supply
reflected radiance and must not be described as an appearance fix. Source/material
ownership, coherent GPU shading/publication and partial surface-water traversal
are still required. Sequence timing includes capture/GL-query overhead.

Experimental Mod SHA256:
`c20e3b8d9302bd754812ea15d90069b62703a03dbe0c80f543027bf79126ee35`.
The client exited normally; `runtime-restored.json` verifies exact normal
configuration/mods and unchanged ordinary-save bytes. No save was rolled back.
The overall goal remains active.
