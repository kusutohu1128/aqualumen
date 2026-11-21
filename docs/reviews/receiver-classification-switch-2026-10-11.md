# Receiver cell classification hot path

The actual v82 JFR recording identifies `LoadedReceiverWorld.receiverCell` as
the nearest receiver frame in 132 sampled Render-thread stacks. Within receiver
stacks, `ImmutableCollections$SetN.probe` is the leaf in 40 samples. These
counts support investigating fixed-ID classification, not exclusive timing
or a frame-time speedup estimate.

`ReceiverField` now uses Java String switches for its exact 16 opaque vanilla
IDs and three air IDs. The previous air check constructed `Set.of(...)` inside
every eligible classification call; the opaque test used immutable-set probing.
No supported ID, collision/full-solid/fluid prerequisite, unknown admission,
chunk access, owner guard or radiance qualification has changed. Equality is
still based on string content, not interned-string identity.

The independent test oracle retains the old sets and evaluates 16,400 cases:
all supported IDs, air/water, selected unsupported plants/transparent/modded
IDs, 1,000 unknown names, and all 16 combinations of the four geometry/fluid
flags. Each uses a distinct String object. Both eligibility and resulting
Cell match the oracle. Existing bounded-ray/slab, source-volume and run-radiance
composition/publication tests also succeeded.

The complete Mod build succeeded:
`build/aqualumen-physics-0.3.0-classification-switch-v85.jar`, SHA-256
`262851e98b495fc2ecfc672680c209e41ad8b9c987658cd38cdef9ab89244e1b`.
It includes the previous unchanged-frame clock guard and owner comparison.
It is not installed. Reduced source-level work is not a measured JVM allocation
rate or actual Minecraft FPS improvement; fresh unprofiled runtime evidence is
required. This does not by itself fix missing reflection geometry or the
folded underwater sky rim, and the full rendering goal remains incomplete.
