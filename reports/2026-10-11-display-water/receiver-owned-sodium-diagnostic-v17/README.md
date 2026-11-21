# Actual upward-face naming diagnosis

Actual material scan reported seagrass at (448,46,-384) as UNSUPPORTED and gravel
at (448,45,-384) as OPAQUE. Dedicated Sodium meshing reached the pre-push callback
with matching renderer/world/cell/state and one face, but normalFace was POS_Y.
The initial adapter incorrectly expected the Minecraft direction name UP, so
it retained unready input. `source-runtime.log` is failure evidence, not positive
source ownership. The next candidate normalizes the pinned Sodium name only.
Normal configuration/mods and ordinary saves were verified/restored exactly.
