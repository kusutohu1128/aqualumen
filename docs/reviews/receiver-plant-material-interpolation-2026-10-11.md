# Owned plant material interpolation

`ReceiverTerrainState.decodeMaterialGeometry` now decodes each captured Sodium
model vertex through the pinned vertex-shader decoder, retaining its actual
world position (including model offsets), UV, block/sky lightmap, tint RGB and
separate AO. It emits triangles in the same `(0,1,2)/(0,2,3)` order as the
existing plant intersection packet. Epoch mismatch, invalid attributes or
degenerate triangles fail closed; no partial decoded list is returned.

`ReceiverMaterialTriangle.sample` produces a `ReceiverMaterialPoint` with
convex barycentric interpolation of all eight material channels and world
position, plus the unit geometric normal. Explicit reversal is available for
the other side; it is not an invented UP normal. This remains a geometric
normal policy, not proof of equivalence to every original vertex-normal path.

The existing opt-in plant diagnostic now checks every material triangle vertex
against its intersection packet: identical primitive order, relative uploaded
float positions, U and V. This diagnostic check is implemented but has not yet
executed on actual models in Minecraft. Ordinary plant traversal remains off.

CPU tests cover vertical triangles, world positions, endpoint values, separate
channel interpolation, reversed normals, invalid barycentric weights and
degenerate inputs. The complete Mod build succeeded as
`build/aqualumen-physics-0.3.0-plant-material-guard-v89.jar`, not installed.
No GPU material draw/readback, live vegetation shading, full owner-completeness
proof or visual improvement is claimed. The next actual test must validate
decoded model/packet correspondence and shade the matching material points
through the original source shader before publishing reflected leaf sources.
