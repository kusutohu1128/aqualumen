# Receiver lighting intake boundary

The previous actual source draw qualified tinted RGB, block light, legacy-cache
direct Sun and rain/shadow/skylight gates. It did not establish actual Iris source
ownership. This step supplies the read-only intake needed for coherent drawing:
typed current-program uniform copies and actual sky/clear/shadow texture and
sampler bindings, rather than invented sunlight or duplicated lighting settings.

Evidence:

- `receiver-lighting-state-gl-final.log`: actual RTX 3080 Ti / NVIDIA OpenGL 4.6,
  controlled GLFW owner context; value/binding readback, sampler-object override,
  invalid/aliased/missing owner rejection, state restoration and epoch expiry.
- `receiver-lighting-state-build.log`: full experimental physics Mod compilation.
- `build/aqualumen-physics-0.3.0-receiver-lighting-v5.jar` SHA256
  `63a3d75b9af57d8634e51bfcff34edab2ef8bd4d19bd0595f96b1f893e8e934b`.
- `git diff --check` succeeded. No Minecraft client was started and this JAR was
  not installed; normal Lab configuration, mods and worlds were not modified.

Limits: the capture is not scheduled at an Iris draw boundary yet. Texture and
sampler handles are borrowed, not immutable snapshots. Exact-frame/resource
ownership and pack compile-time settings must still be maintained by the source
producer. Material filtering/AO ownership, source drawing/publication, partial
surface-water traversal and actual underwater appearance remain unqualified.
The full display/water goal remains active.
