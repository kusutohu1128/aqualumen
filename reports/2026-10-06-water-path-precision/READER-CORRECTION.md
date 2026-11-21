# Preserve initial reader failure

`iris1440-collect.log` is an initial KeyError from using the JAR label
`aqualumen-physics` as a Fabric ID. The actual recorded `mods` map and pinned
fabric.mod.json use `aqualumen_physics`. Correct the new, not-yet-sealed reader
key only; do not change or rerun the completed Minecraft capture, its source,
identity, original strict report reader or any acceptance gate. Re-run saved
data qualification into NEW log `iris1440-collect-v2.log`.
