# Joint plant DDA v62 — actual receiver traversal, opt-in controlled GPU evidence

The original `waterReceiverFirstImpl` now has an opt-in
`AQUALUMEN_PLANT_RECEIVER` integration boundary. Unlike the earlier standalone
plant probes, the new NVIDIA test executes this same receiver DDA, including its
opaque receiver/source pairing, unknown stops, interface qualification and travel
limits, with a supplied plant lookup backend.

Only under the explicit define may an unknown cell become traversable full water
after `waterPlantCellWaterQualified` proves full fluid and complete geometry. The
plant intersection is restricted to that DDA cell's entry/exit segment, after
existing interface/surface/range qualification. Supplied plant lookup covers
otherwise-known water too, so future spatial publication must include neighboring
model spill, not only plant-owner cells. Opaque cube entries remain authoritative
before plant interiors. The default ordinary shader has no define and therefore
retains the previous trace path.

A visible leaf terminates the DDA with known geometry, actual triangle normal and
travel, but `sourceReady=false`. It cannot borrow the farther cube's radiance,
direct Sun or UP-face qualification. Unknown alpha/model lookup stops unresolved.
Only a transparent, fully-owned leaf path can continue to the existing paired
floor receiver. This is not yet a shaded plant source or an adopted visual fix.

`../native-joint-plant-dda-v62.log` retains fresh RTX 3080 Ti draw/readback proving:

- full-fluid plus complete-model qualification and transparent atlas reach the
  original paired floor receiver at travel 2.5;
- opaque diagonal leaf stops first at travel 1 with non-UP normal and no source;
- unknown alpha, missing fluid/model proof remain blocking;
- an earlier opaque bank at travel 0.5 remains authoritative;
- partial interface rejection and a later unrelated unknown remain blocking;
- previous dense/compressed receiver/source regressions remain passing.

`../native-joint-plant-compile-v62.log` records ordinary shader compile/link only.
Diagnostic builders retain strict source pins for the archived wide-field and
new guarded-source revisions and insert palettes at the terminal header guard,
not inside nested plant guards. Their geometry/source guard and mutation-negative
tests pass. Archived old packs remain unchanged.

The lookup backend in the GPU fixture is supplied synthetic geometry/fluid/atlas,
not live Minecraft publication. No ordinary pack enables this define. No client
was launched or settings/saves changed in this checkpoint. Resource/frame-owned
all-model index publication, actual reflected-ray footprint, selected leaf
material/light shading and real moving-scene acceptance remain required. The
macro must not be enabled for ordinary play without those producer contracts.
The full Sun/underwater-sky/natural-water goal remains active and unachieved.
