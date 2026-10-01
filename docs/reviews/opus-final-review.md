# Completed Claude Opus review

Date: 2026-10-01. Reviewer requested with Claude Code `--model opus`; the actual responding model was **`claude-opus-5-5`**, provider `firstParty`, Claude Code 2.1.284. The successful call completed in 27.306 seconds, one turn, with zero permission denials. It used no tools and reviewed the task-scoped implementation summary in [opus-final-prompt.md](opus-final-prompt.md). It did not claim to run Minecraft or independently measure performance. Minimal model/response/completion evidence is [opus-final-evidence.json](opus-final-evidence.json).

Two earlier broader read-only reviews used only Read/Grep/Glob, no MCP servers, restricted mode and `dontAsk`; they timed out at 420 and 360 seconds before a final assessment. The second did produce actual Opus 5.5 repository-read responses. Full raw transcripts are retained locally under ignored `build/reviews/`, outside the versioned review artifacts; they contain no detected credentials, but omit unnecessary session, signature and account-usage metadata from delivery. The completed focused review is the basis of the findings below.

## Reviewer response

> **Verdict:** The architecture is appropriate for a first useful release. The solver is stable at the clamp limit. Per substep, `c·dt/dx = 2.5·0.025/0.125 = 0.5`, which is below the 2D symplectic-Euler limit of about 0.707. The force kernel has zero net 2D volume, so it does not drift the mean level. Splitting the sky into an LUT and caching solar transmission is sound. Your plan to report 60 FPS separately from limited-scene measurements is the right call.

### 1. Recenter and coordinate consistency

- **Remainder tracking:** Shifting by `(newOrigin−oldOrigin)/CELL` is only correct if the origin is snapped to the 0.125 m grid in world space. Any rounded or fractional remainder must carry over between frames. Otherwise ripples slowly slide relative to the boats and the player.
- **Camera-relative precision:** Verify that the Mod computes the origin in double precision before converting to camera-relative floats. Check this especially far from (0,0).
- **Shifted-in cells:** These should be zeroed, not sampled at the edge. Zeroing at the outside-domain read handles this only if begin applies it after the shift.
- **Test:** Sail in a straight line for several minutes and confirm a stationary wake does not drift or shear.

### 2. Source sampling and plane gating

- **Small radii:** A radius below about 2 cells (0.25 m) undersamples the kernel. The force then aliases, loses its zero-mean property, and produces grid-aligned spikes. Clamp the radius to at least about 2·CELL, or integrate the kernel over each cell.
- **Plane gating:** Gating to the nearest plane makes any water at the same Y within 32 m show ripples. That includes separate ponds, the far side of walls, and under-ice water. It also makes flowing water and waterfalls show mismatched ripples.
- **Mitigations:** Add a vertical tolerance plus a per-pixel fluid-level check. Also fade the ripples out on non-source and flowing blocks.

### 3. LUT row bleed and frame-time edge cases

- **Row bleed:** Bilinear sampling near row 127 can pull in values from the reserved transmission row. This causes a horizon or zenith band. Clamp `samplesky` UVs to half a texel inside the 127-row region, or use `texelFetch` for the reserved row.
- **Frame-time edge cases:** Make sure elapsed time is zero when the game is paused or a menu is open. Also confirm begin/begin1 run exactly once per frame, not again for the shadow or other passes. If not, the ripple speed will scale with the pass count.

### Lesser risk

SSR falling back to sky above water will look wrong under overhangs and in caves. Gate the fallback by skylight as well.

## Codex disposition

- The image solver's CFL and zero setup were independently checked on the actual NVIDIA GPU. The force's continuous-plane integral is zero analytically, but discrete samples, domain edges and damping can change that; this is a linear interaction-height model, not a water-volume conservation claim.
- The final release enlarged the sky LUT to512x256. Solar transmission uses `texelFetch(ivec2(0,255))`. `sampleSky` remaps its vertical coordinate to texel centers from `0.5/256` through `254.5/256`, so bilinear samples do not touch the reserved row255. The original review above discussed the earlier256x128 layout; the row-bleed mitigation is unchanged.
- Final source verification confirms the absolute double-precision snapped origin, matching shift sign, per-frame deduplication, paused delta zero and source radii 0.30/0.65 m. A water-only contiguous-column probe replaced the original highest-fluid scan. Same-height disconnected pools still require a topology mask for complete isolation and remain a model limitation; see [companion-final-audit.md](companion-final-audit.md).
- The cave SSR fallback now gates by sky exposure, as do direct water sunlight and caustics. The shader compilation and real-world benchmark artifacts, rather than this review verdict, determine runtime acceptance.

## Sunlight implementation and validation

The baseline six uniform optical-depth samples were replaced with sixteen quadratic intervals concentrated near the observer. At a solar elevation of 90 degrees, the Mie optical-column error versus a 12,000-segment reference decreased from -98.66% to -5.16%; Rayleigh-column error is -0.81%. At 5 degrees, Mie error decreased from -90.28% to -3.32%. This verifies quadrature improvement for the declared atmosphere, not calibrated real atmospheric data.

Direct sunlight is cached in the sky LUT. Terrain uses skylight as an extra direct-light occlusion gate; air fog uses smoothed camera skylight to suppress outdoor haze in caves. The lower sky hemisphere traces to a diffuse ground approximation rather than repeating horizon radiance. A fixed full-moon disk/direct-light approximation and modest Nether/End fallbacks were added. Sun-disk exposure, multiple scattering, moon phases, caustic bottom occlusion and world-space offscreen reflections remain explicitly approximate.

`make check` passed on NVIDIA GeForce RTX 3080 Ti / OpenGL 4.6.0 NVIDIA 580.173.02: all eleven program pairs, GPU Fresnel/TIR/Beer-Lambert probes, and the GPU wave-height setup/response/CFL/recenter/decay/teleport probes. This check is not an in-game FPS measurement.
