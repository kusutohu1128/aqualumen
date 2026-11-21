# Source pass initialization attempt

The new Iris prepare1 shader loaded and the near scene completed without
fallback. However, the receiverInputSize supplier was invoked during early
initialization with program 0 and a shadow-sized FBO. Its attachment receipt
does not describe prepare1 and must not be treated as source-target evidence.
`source-runtime.log` retains that failed observation. The next candidate moves
the observation to the pinned Program.use tail after binding and updates.

This run supplies no natural material/radiance and is not an appearance fix.
`runtime-restored.json` verifies exact normal configuration/mods and unchanged
ordinary-save bytes without save rollback.
