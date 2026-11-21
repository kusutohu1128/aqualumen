# Depth consistency design rubric

Score0to2 per criterion, choose no design that fails the first two.

1. One authoritative solved first-hit point controls depth and water eye attenuation without mixing opaque distance or inventing medium membership.
2. Unsovled, air, nonwater and closer opaque/translucent behavior remain explicit and testable; no ghost water or overwritten occluders.
3. Same-frame actual depth and post-composite distance/transmission can be observed with exact sampler/state proof and limited diagnostics.
4. Small original implementation reuses frozen generators/runtime and keeps all old evidence immutable.
5. A fail-first test detects the old depth inconsistency; candidate invariance and negative controls are nonvacuous.
6. Root model, shadow/receiver origins, numerical and general-world limits are stated without overclaiming visual or performance completion.
