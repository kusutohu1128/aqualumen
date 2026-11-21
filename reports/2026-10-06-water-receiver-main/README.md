# First-world-source water MAIN candidate, not a release

This packet advances the original renderer's qualified occluded-first-floor
REDs. It does not install a source producer, change the ordinary shader ZIP,
or establish the full realistic-water/sunlight/physics goal.

## Original fixture unchanged

`native-v2` and final `native-v3` use the byte-identical original native-v4
closed-box fixture/observer and the same complete external input textures.
The only public shader settings are the existing flat `WAVE_HEIGHT=0` and
`SHORE_FOAM=0`. Every binary is built synchronously to a unique path; full shader
and fixture sources, compile log, raw GL readbacks and receipts are retained.
The independent reader uses the same Snell, slab intersection, Fresnel, Beer
and unchanged 2-percent acceptance, checking nine hidden-footprint points,
first opaque source ownership and actual outgoing path as well as color.

RTX3080Ti / NVIDIA580.173.02 / GL4.6 actual native results:

- Camera-hidden first floor: green gain `0.05931365489959717`, independent
  expected `0.059313650899358396`. Prior qualified gain was zero.
- Visible first floor: `0.02615226060152054`, expected
  `0.026152266381846888`, within the original tolerance.
- Closed near-first floor: farther-tag RGB difference zero, formerly
  `0.09272925555706024`.
- Passive observation C0 maximum difference zero; actual first paths agree
  with independent intersections to less than `1e-5` metres.

`independent-audit-v3.json` is the final original-MAIN audit. The historical
v4 RED packet remains unchanged: it proves the original failures, not the
current candidate's final results.

## Incremental unready-first control

Only external near-floor source alpha becomes unready. Geometry, far source
readiness, shader options, screen input, oracle and pixels are unchanged.
`unready-red` reproduces the same `0.09272925555706024` farther-color leak.
`unready-green` rejects that borrowed source with zero RGB difference, preserving
the actual `0.7371301805333212` metre first-object path. Kind4 denotes known
geometry with unknown-source environment fallback, never guessed sand radiance.
The reader also checks every source RGB/alpha against the declared one-variable
edit. This is a real RED->GREEN increment, not a weakened visible-positive test.

The final `absent` control sets only input readiness to zero. Its independent
reader compares four entire C0 and seven whole observed-state fields with the
sealed original native-v4. Its two legacy REDs are expected compatibility
evidence, **not** success of the new source path or waived release defects.

## Retained gates and rejected attempts

`retained-regressions` runs `make check`, the absolute direct-radiance observer,
and the retained nonzero-wave first-visible-bed test, on actual NVIDIA in an
exclusive frozen source/build tree. Native timings are not Minecraft timings.
The five focused public audit tests reject missing hidden response, farther
borrowing, wrong path and nonpassive observation; no internal modules are mocked.

The first compilation (`native-v1`) rejects GLSL reserved identifier `layout`;
its sources/log/receipt are preserved as **inconclusive**, not a qualified RED.
The pre-rename radiance observer rejects duplicated passive-store anchors.
Its raw preparation and log remain; only the new world's local names changed,
not the original observer, existing screen-path variables or physical thresholds.

## Exact remaining scope

Input source is synthetic, already air-lit **linear homogeneous-voxel radiance**,
not actual sand/atlas shading. Only declared full-water segments are traversed;
unknown, air, unsupported, ambiguous and out-of-window paths do not become
guessed all-water optical hits. DDA dimensions/travel/steps are bounded. Source
RGB and direct attribution are separately validated; absent paired Sun is only
admitted by a zero actual receiver solar cache in the qualified fixture.

The normal bridge still registers no receiver producer. Actual per-face atlas
sampling/LOD, Sodium light/AO or declared coherent shared source lighting,
geometry/material/atlas epoch coherence, dynamic Iris binding, full fluid-volume
membership, nonzero world-source Sun tests, moving/tessellated interface joining,
natural Minecraft images/motion/timings remain unaccepted. The native full suite
retains existing optics/lighting/wave behavior with new readiness default zero;
it does not establish these new live source requirements.

Ordinary post-save baseline is fresh. No ordinary save was restored, no world
commands issued and no TEST instrumentation installed this cycle. Normal
0.6/physics0.2 restoration/reopening evidence is recorded in `checkpoint.json`;
there are no native GPU calls after that handoff. Old sealed packets/releases
and the full goal are preserved.
