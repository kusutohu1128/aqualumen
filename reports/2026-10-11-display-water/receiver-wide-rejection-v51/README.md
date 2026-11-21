# Wide-field rejection v51 — actual optical diagnostic, not a rendering fix

The diagnostic builder now separately instruments the exact pinned wide/run
receiver revision (`af98491f4669ef591d99b1d942402678dd84f654ac9c72e18f48eef81a2a3ad5`).
It preserves geometry/source guards and splits face readiness from wrong-normal
rejection, and interface permission/corner/segment failures. Original physical
sources and the v50 ZIP remain unchanged. ZIP comparison verified only the water
fragment and receiver library changed. Five builder and nine runtime safety tests
pass; retained v33 instrumentation remains pinned to its own archived revision.

The exact diagnostic pack compiled/linked on RTX 3080 Ti (native v51 log).
This receipt is compile/link only, not controlled rendered-branch verification.
Actual Minecraft ran Mod v56, the 87×36×87 field and the same two UUID-guarded
underwater scenes. Source publication/bindings remain live; static/moving captures
completed and auto-quit. Native-motion audit verified 58 PNGs, launcher exited
zero, Java stopped, and normal config/Mods/ordinary-save hashes restored exactly
without ordinary-save rollback. Diagnostic timing is not normal-renderer timing.

## Palette and reviewed evidence

The final water diagnostic overrides only fully TIR pixels (Fresnel >=0.9999).
Dark neutral center is non-TIR and must not be counted as failure. Palette:

| Color | Meaning |
| --- | --- |
| Green | Qualified paired world receiver source |
| Pale blue | Ordinary screen-space reflection hit |
| Red | Left the receiver window |
| Orange | 48-metre range bound |
| Blue | Unknown/unsupported geometry kind |
| Cyan | Failed below-interface segment qualification |
| Yellow | Missing interface corner qualification |
| Purple | Known opaque run without an eligible source address |
| White | Source face normal differs from first-hit normal |
| Pink | Missing face/source/paired direct-light readiness |
| Magenta | Compressed lookup failure |
| Gray | Parallel-boundary or crossing tie |
| Other warm neutral | Other guarded early return |

Actual static `frame-027.png` and moving `frame-029.png` were viewed. Blue unknown
geometry occupies broad exterior patches in both; green source hits are now
substantial. White wrong-face regions are visible in the static frame, consistent
with UP-only source coverage. Red field exits remain but no longer explain all
the exterior. Cyan segment failures are small in these reviewed frames. This
does not prove every frame, wave phase or underwater scene behaves identically.

`diagnostic-display-counts.json` records approximate display-color counts for
those two frames, not exact shader branch counters or linear radiance. Static:
228610 blue-like pixels versus 7335 red-like, and 108516 green-like. Moving:
247382 blue-like versus 37139 red-like, and 216679 green-like. Neutral and combined
palette categories are intentionally ambiguous; absence of a neutral count does
not prove absence of wrong-face rays in the deeper view. Antialiasing/transport
and display conversion prevent treating these heuristics as exact per-ray data.

## Next causal work

Do not keep widening the field on the assumption that the older narrow-field red
diagnostic still dominates. Subdivide unknown geometry using actual producer
classification: unqualified air/water, unloaded, unsupported vegetation or other
shapes, without changing kind=unknown or admitting rays. Current kind zero loses
those reasons, so this run does not establish which subtype dominates. Then
address confirmed coverage while preserving first-object/alpha/shape ownership.
Wrong-face regions require their own actual material/light source; borrowing UP
radiance for another face or forcing unknown rays into sky/floor is not a fix.
The folded sky-window shape, coherent Sun appearance/transport and usable
performance remain open. This diagnostic is not normal-runtime adoption.
