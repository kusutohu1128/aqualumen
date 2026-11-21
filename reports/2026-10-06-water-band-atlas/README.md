# Saved diagnostic-atlas band localization (CPU-only)

Continuation of the unachieved water/sunlight realism goal. The previous goal
turn made progress: actual Iris observations completed, four-role geometry
identity qualified, and ordinary0.6/physics0.2 safely restored. It did not fix
the remaining fine dark contours.

This packet reads the already saved phase0/45 diagnostic PNGs. It does not
rerun Minecraft, GPU fixtures or the completed phase0 physical benchmark.
The prior114-entry continuation checksum manifest verified with exit0 before
analysis. Current tracked diff retains22 files /1517 insertions /102 deletions.

Current environment allows writes only in the repository and /tmp. NVIDIA
device nodes are absent. The old8034 process handle is no longer available to
the current tool session; that is not proof of an observed clean client exit
or current host play state. No host launch/config/world action is attempted.

The atlas has four400×450 tiles per row. C0 is bottom-left; full/base WR panels
are top columns1/2; outer flags are bottom column3; TES is top-left. Analysis
excludes the bottom1/8 alpha stripes and uses only decoded displayed RGB.
Its binary WR valid/applied values are screen encodings, not raw RGBA32F or
fresh same-frame per-fragment proof. C0 brightness comparisons are encoded
PNG values, not calibrated physical luminance. Native passivity qualification
does not silently qualify actual Iris image readback.

Ranked falsifiable hypotheses are unchanged in scope:

1. Whole-result admission: dark pixels track full/base rejection in this atlas.
2. Finite quadrature response: phase changes dark features without changing
   the application mask at those positions.
3. Mean receiver/handoff: features instead track outer receiver/flags changes.
4. Geometry edge: features track TES boundary locations irrespective of phase.

Counts, brightness association and proposed future probe coordinates will be
recorded as descriptive saved-image evidence, never physical acceptance. The
original16-point qualifier remains intact; band points must not replace it or
waive its minimum4 Sun application gate. No physical shader/Mod fix is asserted.

## Findings and coordinate qualification boundary

[Initial associations](atlas-association-initial.json) and
[crossphase comparisons](crossphase-association.json) describe152478 eligible
display positions per scene. Full-WR displayed rejection counts are82/72 near,
72/70 deep and2076/2291 tilt for phase0/45. At deep positions,42/72 and46/70
rejected pixels have encoded local brightness drops greater than8; accepted
positions have150/152406 and178/152408 such drops. This is a descriptive screen
association, not a controlled causal effect, radiance measurement or band fix.
The displayed phase-rejection XOR counts are154 near,90 deep and4037 tilt.
Outer/TES RGB displays are unchanged at these analyzed positions. None of this
supersedes the independently qualified original16 **raw** samples.

Four full/base display disagreements occur in tilt at local atlas column278:

| Local top-origin Y | Phase with disagreement | Full applied / base applied / Sun applied |
| --- | --- | --- |
| 359 | 0 | 1 / 0 / 0 |
| 365 | 45 | 0 / 1 / 1 |
| 372 | 45 | 1 / 0 / 0 |
| 374 | 45 | 0 / 1 / 1 |

The second/fourth rows conflict with the source Sun gate requiring both legacy
applications, **if** the displays are the same invocation and pixel. That
condition is not established. Do not interpret these as proved raw shader
gate violations or use them to justify changing the physical admission policy.

[A binary32 arithmetic counterexample](uv-rounding-counterexample.json) shows
that the old `texcoord*grid-tile` then float-to-integer expression does not
guarantee identical texel selection across panels. Under the explicitly
modeled no-FMA arithmetic,219/400 local columns differ; local column3 selects
source X14/13/13/13. **Column278 does not differ in that model.** Thus the
counterexample does not explain the four disagreements above. Actual Iris
varying interpolation, optimization, texture extents and draw freshness are
not reproduced by this CPU model. Stale/different pixels remain alternatives.
All JSON `source_x/source_y` fields from old screenshots are **nominal** ideal
addresses, not certified actual fetches. They must not be promoted to a raw
band-pixel oracle without a new coordinate qualification.

## New reversible diagnostic-only candidate

[Builder](../../tools/water_atlas_aligned_pack.py) wraps the two pinned original
diagnostic ZIPs without modifying any frozen source, ZIP or report. It changes
only `shaders/final.fsh`'s coordinate block, using integer `gl_FragCoord` tile-local
address arithmetic and a selected texel-center UV. Physical MAIN, water C0
buffer, all seven record writers, Sun48, GH rotation, receiver/admission logic,
VS/TCS/TES, allocation and guards remain byte-identical to each parent.
The C0 **display sample coordinates** deliberately change; unchanged AA/tone
arithmetic does not imply byte-identical panel appearance or proven passivity.

Generated, **not installed or accepted**:

- [Phase0 aligned-v2](cpu-pack/Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-aligned-v2.zip),
  SHA256 `90c7d9dc1d98dfd45ff050f2f08e0bd516b756a1109dd19d738d969723da341d`.
- [Phase45 aligned-v2](cpu-pack/Aqualumen-ShoreProbe-world-gh-phase-45-diagnostic-aligned-v2.zip),
  SHA256 `b8bd19dff8c61b83311168e10eaa5704d2271ac805890404d4781cc316608069`.

The added `WATER-ATLAS-ALIGNED.json` is the current FINAL descriptor. The retained
`WATER-GH-PHASE.json` is historical parent metadata, not authoritative for the
new FINAL. Embedded original parent ZIP recovery is exact and tamper-checked.
The frozen runtime auditor rejects both the new filename and an old-name alias;
never relabel these artifacts or mutate saved raw evidence to bypass it.

[CPU tests](cpu-tests.txt):7 passed. These cover the old arithmetic counterexample,
integer separable-axis address properties covering all local pixels/eight
tiles at1600×900 and2560×1440, FINAL-only deltas, exact recovery, deterministic
ZIP reconstruction, overwrite/alias/tamper rejection and frozen-auditor refusal.
The initial missing-builder failures were scaffolding failures, **not** a
reproduction of the Minecraft visual bug. These tests do not execute GLSL,
qualify actual GL arithmetic/bindings or demonstrate that the black bands vanish.
No new GL compile, Minecraft run, FPS measurement or physical acceptance occurred.

## Intended next host action

1. Keep ordinary0.6/physics0.2 and recoverably disabled TEST files untouched until
   an authorized host/GPU run can use the previously isolated Lab/V2 exact UUID.
   The Oct5 completed physical phase0/45 and four-role geometry-pair observations
   must be reused; do not rerun them simply because this packet is new.
2. Qualify the new FINAL on actual NVIDIA/Iris, including zero-origin viewport,
   viewport=viewWidth/viewHeight=all seven full-size attachment extents and
   every panel's actual selected texel address. A native GL source pass alone
   does not qualify actual Iris display/binding or same-invocation freshness.
3. Add a separately named/pinned aligned-v2 runtime qualification. Preserve the
   original16-point readback and minimum4 Sun gate; do not widen the old auditor
   or alias filenames. The new candidate is not yet a drop-in qualified run.
4. Only then obtain aligned phase0/45 diagnostic tilt observations, and a
   separately tagged bounded raw band-point packet **in addition to** the
   original16 samples. The four nominal target coordinates are(1114,181),
   (1114,169),(1114,155),(1114,151), bottom-left origin. Their relevance must be
   freshly verified, not assumed from old images. Jointly qualify actual
   full/base WR, Sun status/reasons, outer state, TES, C0/call and coordinate
   freshness at the same invocation; preserve numerical values without display
   decoding. Do not mix in density, optics or geometry changes.
5. If address-aligned/raw observations still contradict the Sun gate, investigate
   routing/freshness first. If raw rejection actually tracks dark contours,
   design one physical admission experiment with energy/boundary acceptance;
   otherwise return to finite integration/receiver/geometry hypotheses.
6. Recoverably disable instrumentation and verify ordinary configuration and
   world scope again after any future TEST run. Never restore a whole save copy.

This turn made CPU/instrumentation progress; the full goal remains active and
unachieved. No commit/push, live install, world modification, GPU-speed claim,
physical band fix or renewed ordinary-client play-state claim is made.
