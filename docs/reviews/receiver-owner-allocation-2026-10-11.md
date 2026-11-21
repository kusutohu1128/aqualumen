# Receiver owner guard allocation reduction

The v80 natural capture remains around 1.4 FPS. The existing source producer
performs hundreds of thousands of geometry reads, with owner checks on each
public read. Previously each check called `ReceiverRadianceBridge.epoch()`,
constructing an `Epoch` solely to compare its world/frame/resource fields with
the immutable lighting snapshot. This is unnecessary transient work in the
collection and validation hot paths.

`ReceiverRadianceBridge.lightingCurrent` now observes the same Contacts state,
dimension, Iris activity, pack-name prefix, frame counter and resource
generation, then compares primitive fields directly. `Epoch.matches` retains
world reference identity (not world equality). `ReceiverLightingState.current`
uses the same comparison for its existing object-based API. The source owner
still checks thread identity and current validity for every read; guards were
not amortized or disabled. No previous-frame geometry/radiance is reused.

Validation completed: radiance volume/publisher CPU suite, source-volume CPU
suite, model-state witness CPU suite, and complete physics Mod compilation.
The new unique artifact is
`build/aqualumen-physics-0.3.0-allocation-free-owner-v83.jar`; it has not been
installed. This change removes explicit source-level allocation, not a measured
allocation rate: JVM escape analysis may already eliminate some allocations.
Actual Minecraft timing improvement remains unmeasured, and this is not a
solution to missing reflection owners or a usable performance acceptance.
