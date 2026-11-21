# Rejected detached-stage reuse

The corrected profile-dependent polygon-state guard passed, but the next live
attempt found no attached source stages on the Iris fullscreen program. The
pinned ProgramBuilder destroys its GlShader objects after ProgramCreator returns;
the linked program remains usable without retrievable attached shader objects.
No shaded RGB was accepted or published. The near-view test completed and exact
normal config, Mods and ordinary-save hashes were restored/verified without
save rollback. `source-runtime.log` retains the actual rejection. The next
implementation observes the actual compiled source before shader destruction.
