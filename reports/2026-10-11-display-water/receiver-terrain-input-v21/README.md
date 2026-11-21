# Current terrain-draw input ownership

The observer now runs immediately before the pinned Sodium multi-draw, rejects
nonterrain fragment programs, and copies that draw's live lightmap matrix and
UV shrink. It observes the actually bound terrain atlas and effective comparison
sampler, restoring the active texture unit. No texture, sampler, program, vertex
buffer or ordinary terrain draw is modified by these reads.

The owned synchronous gravel face is captured and decoded within the same
world/frame/resource epoch as this terrain draw. At frame 3/resource generation
1, program 418 used atlas 22 (1024x512), sampler 0. The face-center attributes
were UV (0.4296875,0.484375), block/sky (0.0625,0.0625), white tint and AO
0.7980392. The raw packed light remains zero: stock Iris light-byte clamping
and the actual matrix produced these decoded values. No artificial skylight or
AO was substituted. `source-runtime.log` retains actual packed vertices and
center/local derivatives.

The local S/T derivatives are not camera fragment gradients or a reflection
footprint. The atlas/sampler are borrowed handles, not immutable pixel copies;
an epoch alone does not guarantee later contents or resource lifetime. This
checkpoint performs no filtered atlas draw, shared lighting evaluation or
natural radiance publication. Source input size remains zero. Vegetation and
partial surface water remain unsupported by the optical traversal.

`../receiver-terrain-input-decoder-test.log` compares the existing CPU decoder
against 448 archived actual GPU vertex floats and checks unavailable inputs.
That test is historical decoder evidence, not GPU shading of the new live face.
The actual near-view run used NVIDIA/Iris without fallback; native PNG validation
is not visual/FPS acceptance. The full Sun/underwater-view goal remains open.

Experimental Mod SHA256:
`32ea9fec20ece074bff09bf514a0a19c1e832f1b0a8b74daeed8e53a39c4a263`.
The client exited normally. Normal config, Mods, instance settings and ordinary
save hashes were restored/verified exactly, without save rollback.
