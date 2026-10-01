# Actual Sonnet contribution: opaque-foreground cloud ghosting

2026-10-02 JST. One successful Claude Code no-tools turn, actual responding model
`claude-sonnet-5-5`, 32.194 seconds. Only three relevant shader snippets and the
controlled GPU reproduction were supplied. No account credentials, unrelated
project data, repository tools, MCP servers or game controls were provided.
Sanitized response metadata is in [the evidence file](sonnet-v0.3.1-evidence.json).
The task-scoped prompt and raw response remain in ignored `build/reviews/`.

Sonnet proposed splitting the existing atmosphere LUT into a cloud-bearing sky
(`colortex6`) and cloud-free atmosphere (`colortex7`), writing both from the same
`prepare` pass. Only foreground aerial haze samples the second texture. The
visible sky, water reflections and cloud-attenuated direct solar cache retain
the first. Atmosphere integration is shared, not calculated twice. Codex reviewed
and applied this patch; Sonnet explicitly did not compile it or run Minecraft.

Before application, a deterministic GPU test executed the production composite
shader with identical opaque foreground color, depth, illumination and atmosphere.
Changing only background cloud radiance by +4 changed the foreground red channel
at 128 m from 0.0713577 to 0.640898, despite alpha remaining one. The assertion
failed before the patch and passed afterward. Expanded 16/64/128 m tests and a
production `prepare` multiple-output/solar-cache test are Codex verification,
not independent Sonnet runtime evidence. See the [release report](../../reports/2026-10-02-v0.3.1/VERIFICATION.md).

The additional caustic derivative placement and Earth-dimension gate were Codex
changes. Pixel footprints are now evaluated before varying caller branches and
passed into the helper. This is a source-level correctness fix; it is not a
reproducible proof of the cause of every shoreline artifact. The footprint uses
the original view-ray receiver, not a reconstructed offscreen refracted receiver.

The prior Opus review concerns the 0.2 architecture. No fresh external Opus
approval is claimed for this release.
