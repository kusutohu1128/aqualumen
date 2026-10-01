# Companion Mod final source audit

Date: 2026-10-01. Scope: `physics-mod/**`, the local image solver and its water-geometry interfaces. This is source inspection plus GPU harness validation, not a claim of completed Minecraft interaction/FPS validation.

## Confirmed dispositions

- `Contacts.update` uses `SystemTimeUniforms.COUNTER` to take one shared snapshot per rendered frame, even when multiple Iris notifiers request uniforms. The two compute passes each consume half the shared frame delta. Source radii are 0.30 m for ordinary contacts and 0.65 m for boats, above the reviewer-recommended 0.25 m minimum.
- The grid origin is computed from the unshifted camera in double precision and snapped with `floor((camera-32)/0.125)*0.125`. Recenter shifts use `(newOrigin-oldOrigin)/0.125` before converting to float. Camera-relative grid/contact values are converted to float only after subtraction. `begin` copies input at `p+shift`, the correct overlap relation for that shift sign. Outside-domain reads produce zeros; teleports, world changes and water-plane changes trigger reset.
- `MinecraftClient.isPaused` sets the wave delta to zero. Otherwise elapsed time is clamped to 0.05 seconds, bounding per-substep CFL at 0.5. Inventory/multiplayer screens that do not pause Minecraft do not freeze the simulation; this follows game pause behavior rather than treating every screen as a paused game.
- Candidate contacts exclude lava-touching entities and spectators. Only nearby rendered world entities are read, and the eight closest suitable sources are retained. Their real movement produces bounded force; stationary contacts decay. The Mod never sends Minecraft commands, changes blocks/entities, sends chat, or opens network connections.
- Its one intentional local write is the once-per-second diagnostic `config/aqualumen-physics-status.json` under the current Minecraft game directory. This is runtime evidence, not a world mutation. Shader-pack identity is checked before activation; failure turns forcing off safely.
- Root corrected the audited water-plane bug: the old scan selected the highest nonempty fluid within 12 m, potentially choosing lava or an unrelated upper pool. The final probe finds nearby water within three blocks and follows only that contiguous water column upward, bounded at 32 cells. Fluid identities were verified against pinned Yarn mappings: `field_15910=WATER`, `field_15909=FLOWING_WATER`, `method_15772=getFluid`, `method_20785=getHeight`. The revised probe stops at the first nonwater cell and does not cross a gap to an upper pool.
- Water vertex displacement and fragment normals gate the interaction field to a 0.30 m band around the chosen plane. Water sunlight, caustics and sky-reflection fallback also gate by sky exposure, addressing the review's cave reflection concern.

## Remaining model limits

The field has no full water-topology/bathymetry mask: disconnected ponds at the same height within the local domain can still share height waves, and horizontal flowing-water faces cannot be completely classified by the shared water material ID. The amplitude/gradient clamps and absorbing border stabilize visual interaction but are not a mass-conserving fluid boundary solver. Only one local water plane is simulated at a time. These limitations should remain explicit in release documentation.

The active field persists for up to ten seconds after a real contact or successful camera water-column probe; its approximately 0.8/s base damping dissipates old waves. Deep columns exceeding the 32-cell probe bound fail closed instead of inventing a surface. Large-coordinate long-distance sailing, pause/resume, shader reload and overlapping-water scenes remain useful real-game checks even though the source logic and GPU recenter tests are consistent.

## GPU check

The added atmosphere probe compiles the pack's settings, uniforms and atmospheric functions, explicitly sets the Overworld dimension and renders `solarTransmission(vec3(0,1,0),2)`. The actual NVIDIA result is blue transmission **0.749133**, within 0.01 of the declared 16-interval expectation 0.74913 and close to the independent dense-integration reference 0.74646. The test catches reverting to coarse uniform sampling, which previously returned approximately 0.80038.

`make check` passed on NVIDIA GeForce RTX 3080 Ti / OpenGL 4.6.0 NVIDIA 580.173.02: all eleven linked program pairs, Fresnel/TIR/Beer-Lambert probes, and image-solver zero setup, response, maximum-delta stability, integer recenter, damping and teleport reset. These results do not measure Minecraft FPS.

## Review artifact hygiene

The actual Opus response/completion was reduced to `opus-final-evidence.json`: model ID, provider, CLI version, tool scope, success status, duration, turn count, permission-denial count and final text. Full raw streams are preserved locally under ignored `build/reviews/`; they are omitted from versioned delivery because they contain unnecessary opaque signatures, session identifiers, socket paths and rate-limit/account metadata.

A structural/raw credential scan found no bearer/API token, credential assignment or email patterns. Every file path accessed by the read-only Opus tool session was inside `/home/kusutohu/repos/aqualumen`. The delivered prompt contains only this task's implementation summary; no environment variables, authentication files, unrelated project content or memory files were supplied.
