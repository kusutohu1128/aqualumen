# Native inverse projection fixture

The first depth regression failed with all composite distances at far=128. Water emitted/stored depth and optical point projection already matched on 2617 pixels. Saved logs are in `reports/2026-10-22-water-hit-depth/native-depth1`.

Independent read-only diagnosis found that the inherited `Fixture` inverseProjection initializer in `tools/water_paired_native.cpp` has 15 scalars. A missing zero shifts its last columns and leaves matrix[15]=0. Composite divides by zero, then clamps infinite distance to far.

The new DepthFixture constructs the correct inverse locally and asserts projection times inverse is identity before drawing. The old native source and prior Evidence stay immutable. Previous bounded color passivity compared identical fixtures, not a valid composite distance path. Old native SSR coverage remains unaccepted. This turn's new composite checks use the corrected matrix and rerun into a new output directory.
