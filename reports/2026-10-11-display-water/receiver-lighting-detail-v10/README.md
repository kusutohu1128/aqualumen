# Actual depth storage diagnosis

The real Iris shadow binding was texture 67 / sampler 2, 2048x2048, internal
format 6402 (`GL_DEPTH_COMPONENT`) with comparison mode 34894
(`GL_COMPARE_REF_TO_TEXTURE`). The first adapter accepted sized depth formats
only and incorrectly rejected this valid unsized format. `lighting-runtime.log`
retains the actual rejection. This run is diagnostic evidence, not positive
lighting intake or reflected source production. The near scene completed without
fallback, and `runtime-restored.json` verifies exact normal configuration/mods
and ordinary-save bytes; no save was rolled back.
