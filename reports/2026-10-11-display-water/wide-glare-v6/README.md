# Wider display glare candidate

Three actual NVIDIA/Iris scenes completed without fallback: direct midday Sun,
late-afternoon west-facing Sun, and rotating deep underwater view. The native
sequence audit verified 95 PNGs and actual elapsed-time/camera metadata. The
launcher exited normally and normal configs/Mods/ordinary save bytes were
verified restored/preserved. The normal pack was not replaced.

Visual inspection of the three final native screenshots shows a much larger
bright footprint around the midday Sun and an underwater halo. The bright
midday footprint has a visibly bounded, somewhat square shoulder; it is not
accepted as natural. The afternoon Sun is strongly cloud attenuated and remains
small; changing glare alone does not establish a Sun-size fix in all conditions.
The underwater dark exterior and distorted rim remain unresolved.

The normalized kernel currently truncates at three standard deviations. At the
very large solar HDR source, its tails may still be visible at this finite
boundary even though tiny impulse tests conserve interior energy. A longer tail
or qualified taper must be evaluated rather than claiming the existing oracle
proves smooth appearance. Retained v5 versus v6 images have similar camera/time
but unheld wave/cloud phase; they are not a strict same-frame causal comparison.

Capture overhead is active in all raw timings. These short runs measure the
instrumented workflow, not clean postprocess cost or a 1440p performance gate.
Receiver readiness is still unavailable in the natural runtime, so the optional
world-reflection join does not repair the dark exterior in this packet.
