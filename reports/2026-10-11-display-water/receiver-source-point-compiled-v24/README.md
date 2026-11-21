# Actual shared-source GPU point

The pinned ProgramCreator observer copies the actual compiled receiver fragment
source before Iris destroys its shader objects. A private program links that
unchanged fragment with a gl_VertexID fullscreen triangle; it does not change
the linked Iris program, its uniforms, or ordinary terrain buffers.

At frame 3/resource generation 1, the same-epoch owned gravel top face supplied
the actual encoded/decoded UV, tint, lightmap and AO. A private 1x1 input/output
draw used the currently bound terrain atlas/sampler and the current prepared
sky/clear/shadow resources and copied lighting uniforms. The footprint is an
explicit zero-gradient point, not original camera derivatives or a voxel mean.
The actual GPU outputs in `source-runtime.log` are:

- Total RGB: (0.024670072, 0.020166963, 0.01647116), alpha 1.
- Direct Sun RGB: (0.020955574, 0.016884757, 0.013256727), alpha 1.

Both outputs are finite, nonnegative, paired-ready, with direct no greater than
total. This is actual live shared terrainLight shading of the new captured face,
not only the earlier arbitrary-material native fixture. Atlas/LUT handles are
borrowed only during this immediate invocation; no later resource lifetime is
asserted. These results are logged/discarded, not published to water reflection.
The normal prepare input remains zero-sized and source readiness remains off.

The private draw restores and queries back program/VAO/FBO bindings, viewport,
render enables, indexed blend enables/color masks, texture/sampler bindings and
pixel-pack state before reporting success. It also restores profile-appropriate
polygon mode and active texture, and releases its private GPU resources.
This covers the observed actual state, not adversarial state permutations or
reload/moving-camera publication acceptance.

The near-view test completed on NVIDIA/Iris without fallback; 33 actual PNGs
passed native sequence validation. `frame-015.png` was visually inspected: the
large distorted sky window and broad dark TIR exterior remain. No visual fix or
full-goal completion is claimed. Field scheduling, actual reflection footprints,
bounded source publication, partial surface-water/vegetation traversal and rim
filtering remain required; the Sun appearance gate also remains open.

Experimental Mod SHA256:
`8561d08ea746e49d031b03b55a78131d28691a72045f963fad506de63ddd8501`.
The client exited normally. `runtime-restored.json` verifies normal config/Mods,
instance settings and ordinary-save bytes, without save rollback. The earlier
v22/v23 packets retain their rejected-attempt evidence separately.
