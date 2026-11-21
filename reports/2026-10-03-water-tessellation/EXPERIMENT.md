# TEST-only water geometry stage integration

2026-10-03 JST. Work in progress; no production adoption or completed realism
goal. This packet is separate from the frozen underwater-facet packet.

## Causal scope

First establish a three-point, level-one TCS/TES pass-through with the original
water vertex and fragment logic. The eight production fields, displaced clip
positions, material policy, C0 and depth must be observed, not inferred from
CPU packaging or the existing VS/FS-only checker. C12 records `gl_TessCoord`
and a TES-origin flag; FINAL visibly consumes that flag. Original sources stay
retained in each diagnostic pack. No IOR, fog, exposure or optical-normal change
is authorized in this geometry slice.

Only after native and actual Iris stage integration succeeds may a fixed factor
2/4 experiment reevaluate the existing resolved wave height at generated
vertices. Merely subdividing already displaced planes does not add wave detail.
Topology admission, unknown-column conservatism, shared edges, both windings
and thin bottoms remain required boundaries. Adaptive LOD and a new renderer
Mod are not part of this first slice.

## Ranked predictions

1. Coarse vanilla triangles contribute to the large facets; reevaluating the
   resolved wave on a denser mesh should reduce that particular structure.
2. The fragment normal has more bandwidth than the resolved geometry; density
   alone may leave fine folds. It is not residual-slope energy integration.
3. Missing offscreen reflection receivers will not be restored by subdivision.
   The dark miss fallback is a separate transport problem.

Native observations are a finite empirical qualification, not an all-driver
numerical proof. Diagnostic atlas performance is not shipping performance.
Neither CPU tests nor a linked stage alone accepts the user's underwater view.

## Lifecycle

The ordinary `新規ワールド` paused client was verified with a fresh in-game F2
image, saved all dimensions at 06:03:52 JST, and exited through the verified title
screen Quit button. Owned launcher session 19094 exited 0; host JVM 3626367 and
launcher 3626260 were absent before native GPU work. A new private post-save
world/config backup is for byte comparison only, never restoration. No ordinary
camera, time or terrain automation was performed.

Only the existing UUID/seed-guarded disposable `AqualumenNaturalV2` may receive
test camera/time requests. Root serializes all GPU use and must close each
Minecraft JVM before native GL. Parallel reviewers perform CPU work only.

Source identity before this slice: water VS
`16554f88edf3519481447f22f44b18a06c40881a27504b81e67b58efab266df0`,
water FS `8dfae28a5a98d5c9be4a0e39488cdfe66a01440d2123fd786e83e3e3fcfc0b18`,
shipping0.8.6 ZIP
`16a7da88b7a5ba11d6aadfd56c717875fc61153b81cc859b4503da620c56c9d0`.
The existing checker and its binary were also hash-verified unchanged. Frozen
underwater-facet manifest verification passed all 102 entries.
