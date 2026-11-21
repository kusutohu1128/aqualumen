# TEST-only underwater reflection diagnosis

The exact V2 world ran with the diagnostic pack, NVIDIA and Iris activation
without fallback. The client exited normally; normal configs/Mods and ordinary
save bytes were verified preserved/restored. Native sequence validation checked
100 PNGs, measured timestamps and camera rotations. No visual improvement is
claimed: this is a diagnostic display, not a release candidate.

The production water invocation labels Fresnel >=0.999 with an SSR hit red,
Fresnel >=0.999 with an SSR miss blue, and lower Fresnel green. Its existing
reflection trace runs once, unchanged. The final display bypasses tone mapping,
but intervening production compositing still attenuates labels: do not interpret
literal RGB=255 equality as a label census.

The saved near-upward screenshot has 1,280,000 pixels. Dominant-channel counting
(peak >80, peak >2 times each other channel) finds 198,053 blue miss labels,
1,081,947 green labels, and no red hit labels. This screenshot's full-reflection
exterior therefore uses the production fallback rather than a visible SSR
receiver. The rotating view also visibly has blue exterior and isolated blue
islands; dark small squares may be later particle draws, not confirmed water
receiver failures. The wave phase differs from the earlier natural packet, so
these are not same-frame before/after masks.

The present underwater fallback is scatter radiance. Increasing SSR steps alone
cannot supply a seabed absent from the current camera's depth/color image. Next
work must establish a real reflected-world receiver and its owned radiance,
or explicitly evaluate a bounded approximation without calling it physical.
Retain Snell refraction and total internal reflection. Rough boundary appearance
still needs separate normal/geometry/footprint investigation; this decision
diagnostic does not prove a specific wave slope error.
