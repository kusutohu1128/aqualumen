# Correctness review: water hit-depth TEST unit

I wrote none of these files. I ran nothing: no commands, GPU, game or network. All native numbers below are as you reported them. I did 7 file reads plus targeted greps. I verified nothing at runtime.

## Confirmed correct (no issue)

- **Window depth formula** (`water_hit_depth_test.glsl:16`): matches the GL viewport transform. Fallback depth is `gl_FragCoord.z`, set first thing in `main` (`candidate-passivity/paired/shaders/gbuffers_water.fsh:323`), before the early `return` at :337. So every path writes depth.
- **Fallback view point**: when the hit is not accepted, `opticalViewPos` is `gbufferModelView*worldPosition`, the same expression hit1 used when `opticalPoint==worldPosition` (:367–378, :410). Initial `straightPath` and `shadowVisibility(opticalPoint,n)` change only for accepted hits (:411–413, :435).
- **`DepthFixture` inverse** (`water_hit_depth_native.cpp:16–19`): correct for a column-major perspective matrix, and the product check really computes P·P⁻¹.
- **Straddle logic** (`native.cpp:141–162`): the opaque depth is placed at the midpoint, so hit1 must be wrong in both directions and the candidate must store the expected depth. The ceiling test (:163–164) is sound.
- **Blending**: off for every paired MRT (`shaders.properties:18,33–38,40`). No control pass mentions `colortex2`, so reusing C2 in composite has no consumer that would be disturbed.
- **Depth reader**: the GL enum constants check out. It checks format, base level and comparison mode, and restores active unit, binding and pack state via `preserving`. Aliasing is checked against color samplers and the output attachment.

## Issues, ordered by severity

### 1. High (can decide the verdict): the fixed 1 mm budget is below the depth-storage error floor at moderate distance
Composite rebuilds distance from a single depth value (`composite.fsh:24–27`). The distance error from one depth step is about δd ≈ d²/n · ulp(w).

- With Minecraft's n = 0.05 and ulp ≈ 2⁻²⁴ near w = 1, one depth step equals **1 mm at d ≈ 29 m**. Half a step reaches 1 mm at about 41 m. D24 and D32F behave alike here.
- Your native maximum of 2.13e-5 m at a fixture distance of a few metres fits this d² scaling.
- In an underwater pose, the surface raster can reach far toward the horizon or render distance. If so, `distanceViolations` will be non-zero in both modes from storage precision alone (`water_hit_depth_audit.py:64,81,90–91`).
- The baseline pass condition requires `distanceViolations==0`. Your "matrix readback omitted" caveat depends on the baseline chain passing, so this condition can fail for reasons unrelated to the eye-origin question.
- `ARCHITECTURE.md:41` promises "format- and distance-conditioned numerical tolerances", but :43 and the audit use one global 1 mm. That contradiction is a documentation overclaim.

**To reproduce:** for violating pixels, plot `distanceErrorMeters` against `point_distance`. They should follow d²/n·2⁻²⁴.

**Action:** do not relax the pre-declared budget after the fact. Report the maximum accepted distance and a per-pixel floor alongside the violations. If violations sit beyond about 29 m and match the floor, record the result as a failure of the declared budget, not a contract bug and not a pass. Fix the wording at :41.

### 2. Medium (TEST safety): `stopped()` now fails open
- **Before:** `display_water_runtime.py:44–46` refused if *any* `java` process was running.
- **Now:** `water_hit_depth_runtime.py:9–24,35–36` only blocks a Java process whose `readlink(cwd)` equals `GAME` exactly. It compares unresolved paths (`:18`).

If the live Lab JVM's cwd differs textually, the check reports "stopped" while Lab is running. Causes include a symlinked or bind-mounted home under Flatpak, a launcher working-directory override, or a `" (deleted)"` suffix. `water_paired_runtime.py:120–150` would then write into `mods/` and `shaderpacks/` of a live client.

**To reproduce:** start a same-user Java process with cwd at a symlink alias of `GAME`, then call `stopped()`. It passes.

**Action:** fail closed. Resolve both sides, and refuse if any same-user `java` has `GAME` in `/proc/<pid>/cmdline` or an open fd under `GAME`.

### 3. Medium: exact ties with opaque depth send visible water through the opaque caustic branch, and the verdict ignores them
- Iris draws water with LEQUAL, so a tie lets the water fragment win.
- `composite.fsh:37` then sees `depth==opaqueDepth` and adds opaque-receiver Sun light (`colortex8`) onto a water pixel.
- Ties become more likely once projected depth is written near contacts.
- The audit counts `emittedOpaqueExactTies` (`audit.py:85`) but leaves it out of `boundedDepthEyeConsistencyPassed` (:90–91) and out of `openGates` (:106–111).

**Action:** either fail when ties > 0 or list ties in `openGates`. Do not report a pass as tie-safe.

### 4. Low: the "effective" comparison-mode check may be vacuous
`DEPTH_READER` (`water_depth_candidate.py:100`) reads `GL_SAMPLER_BINDING` through `glGetIntegeri`. As far as I know, core GL treats `SAMPLER_BINDING` as per-active-unit `glGetIntegerv` state, not an indexed target. If so, the call may raise `INVALID_ENUM` and return 0. That would make `effectiveCompareMode` silently equal the texture's own mode.

The same pattern was inherited at `GlReadback.java:51,68`. Please confirm on NVIDIA: after `active(unit)`, call `glGetIntegerv(35097)` and then check `glGetError`. The claim at `ARCHITECTURE.md:35` depends on this.

### 5. Low: depth-stencil formats are accepted without recording the stencil sampling mode
Formats 35056 and 36013 are allowed (`:98`), but `GL_DEPTH_STENCIL_TEXTURE_MODE` (37098) is not recorded. Raw `glGetTexImage(DEPTH_COMPONENT)` is unaffected. Composite's `texelFetch` would return the wrong data if that mode were STENCIL. Record it.

### 6. Low: the `accepted` mask includes 0.0
`accepted=water&(expected_depth>=0)` (`audit.py:60`) counts the `vec4(0.0)` written on non-underwater paths. The helper only produces values strictly inside (0,1). This fails safe today, since the Beer and stored-depth checks catch it, but `>0` matches the contract.

### 7. Low: the capture is not checked against the generated pack hash
The audit records `packSha256` (:75) but never compares it with `archives.paired` in `<mode>/manifest.json`. `configure()` sets the probe but not the pack. A swapped pack would most likely fail rather than pass. Still, `ARCHITECTURE.md:35`'s claim that pack hashes "bind analysis to captures" is not enforced.

### 8. Low: native coverage is narrower than the claims
- `native.cpp:131` skips C3.w<0. Lines :167–171 test only air, unknown-water and non-water.
- So the −2 (projection-rejected) and −1 (underwater, known water, unsolved) fallbacks are **not** natively exercised.
- D24 storage is untested.
- The straddle check predicts results from the unoccluded draw's point (:153,156). It passed, but it does not show the solve is independent of `depthtex1` in general.

"Fallback exact" should name only the three cases tested.

### 9. Low (documentation)
`ARCHITECTURE.md:25` says the in-range check uses `gl_DepthRange`. The helper hard-codes `0<depth<1` (`glsl:18`). This is harmless under Iris's default range, but reword it.

## Scope honesty

- No finding above is an implemented fix for source radiance, R2, raster footprint, coverage, headroom, later translucents or hand, or ripples. Those remain open, and the audit's `openGates` says so.
- The native result (2617 active, 2611 → 0, 2593 → 0) is fixture-level D32F evidence only.
- The old native passivity fixture still has the wrong inverse, so its SSR route1 and exact-color claims stay bounded to that fixture.
- Nothing here proves real Iris draw state, visibility or eye origin. That depends on the near/deep captures passing an audit that issue 1 may legitimately fail.
