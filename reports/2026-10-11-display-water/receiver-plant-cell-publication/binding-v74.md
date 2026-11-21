# Scoped plant data texture binding v74

`ReceiverPlantTextureBinding` scopes the three published plant data textures to
their active sampler2D uniforms, using the units already assigned by the caller.
It requires a current atomic publication and distinct valid fragment units. All
active nonnumeric resource uniforms, including every resource-array element, are
checked for unit overlap before changing GL state. Programs without the plant
uniform contract return no binding; wrong sampler types and aliases reject.

The scope retains original texture and sampler bindings, disables custom samplers
for the exact texel data textures, and restores both on close and failed-open
rollback. The active texture unit is preserved. Context ownership is supplied by
a context-only guard; publisher readiness independently checks the epoch. Cleanup
can restore bindings after shader changes because no shader uniforms are modified.
Atlas ownership, window/reference/LOD uniforms and readiness still need a separate
live producer/draw integration; this scope does not manufacture those proofs.

`../native-plant-binding-v74.log` uses actual Java publication and NVIDIA RTX 3080
Ti draw/readback. Scoped draws match direct publication output exactly for opaque,
transparent and unowned alpha. Nonzero preexisting texture/sampler bindings restore;
duplicate plant units, another active sampler and the second element of a sampler
array reject. An injected post-bind guard failure also restores prior bindings.
Existing decoder/intersection/large upload controls pass.

Full Mod artifact `build/aqualumen-physics-0.3.0-plant-binding-v80.jar` is built but
not installed. No Minecraft runtime or ordinary state was changed. Complete model
coverage, live uniforms/atlas binding, selected-leaf radiance and full water/Sun
visual and temporal acceptance remain open.
