# Receiver geometry contract — concrete implementation, not a rendering fix

The diagnose/tdd workflow preserved the established world-occlusion finding and
introduced a bounded read-only geometry contract. No density, light formula,
wave geometry, screen-space guard, iteration budget or production GLSL changed.
The entire `docs/REALISM_GOAL.md` remains the acceptance scope, not this slice.

## Verified this turn

- New Java immutable capture + first-opaque traversal: actual floor coordinates,
  entry normal and distance; closed first wall blocks the farther tagged floor.
- Explicit unknown/unsupported/unloaded/out-of-bounds/inside/tie/range/finite
  controls, snapshot immutability, transparent/cutout/modded material rejection.
-512 deterministic independently slab-intersected box rays,348 positives.
-3705 independently decoded saved TEST voxels; all16 actual-MAIN refracted rays
  and16 camera rays match the sealed independent oracle's first cube, registry
  identity, distance and normal (1e-10m Java-vs-oracle comparison tolerance).
- Existing bathymetry extraction/cache suite passes; adapter/core javac passes.
  New block-registry signatures checked via pinned local intermediary javap.
- Old world, stop and normal-handoff-addendum SHA256SUMS all pass unchanged.

The first implementation returned UNKNOWN and failed the floor regression.
A second regression found arbitrary ownership of a parallel integer-plane ray;
the conservative boundary rejection fixed it. A third classification regression
failed before the exact vanilla subset implementation. All now pass. v1 retains
the distinct replay-harness reduction-order rejection; v2 predates the final
classification/adapter work. v3 is the current frozen-source replay evidence.

## Explicitly incomplete

No GPU test or new Minecraft run occurred. The optional adapter is not registered,
scheduled, installed or uploaded. The new renderer-level occluded-receiver
production-MAIN fixture, actual atlas/face-UV/tint/light extraction, texture upload,
screen/world optical-source joining and retained renderer/natural-motion validation
remain pending. **The visible shore defect is not claimed fixed.**

The adapter is a read-only full-cube geometry candidate, not arbitrary block-shape
support, water-volume membership, radiance, mass conservation or a fluid simulation.
No new Minecraft FPS result is claimed.

## Ordinary runtime preserved

Owned handle59228 was polled and remains live; host Java3294081 retains ordinary
world lockFD153. Installed0.6 ZIP SHA256:
`6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`.
Installed physics0.2 SHA256:
`1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e`.
Only physics0.2, Iris1.8.8 and Sodium0.6.9 are active JARs. Iris selects0.6 with
shaders enabled; all9 checked opt-in filenames are absent. No game inputs,
world edits, config changes, installs, restarts or native GL calls occurred.
The prior pause image is not re-labelled as a newly verified pause state.

See `RESUME.md`. The full realism goal remains active and unachieved.
