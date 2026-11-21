# Material-position source draw extension

The existing `ReceiverSourceDraw` path used the actual captured terrain
fragment/lighting/atlas but hard-coded every source to an UP normal and its
owner's top-face center. That is unsuitable for a leaf/stem intersection:
borrowing a floor source would shade the wrong surface.

`materialPoints` now accepts an epoch-owned, validated material point with
explicit world position, unit normal and decoded UV/lightmap/tint/AO. It feeds
those values through the same existing GPU material-input textures and
captured original fragment session. The old `points` API constructs its
original top-center/UP inputs and delegates, retaining its supplied decoded
attributes and shader/source-readiness policy. No leaf radiance is invented
and no plant cell is relabeled empty water.

CPU tests cover preservation of supplied data and malformed position/normal/UV
rejection. Complete Mod compilation succeeded in the unique artifact
`build/aqualumen-physics-0.3.0-material-points-v87.jar`, not installed.
These are CPU/build results, not a GPU draw/readback or actual Minecraft
regression of the new API. Old source-draw payload equivalence and real plant
material interpolation must be independently checked before live integration.

Required remaining work: derive material points from actual owned encoded
plant vertices and their barycentric hit, preserve alpha/atlas qualification,
shade corresponding normals/positions, pair total and direct-Sun sources,
publish/bind coherently, and prove complete first-object/model ownership.
This point-sampled source path is an approximation, not a full per-hit material
transport solution or completion of the natural underwater reflection goal.
