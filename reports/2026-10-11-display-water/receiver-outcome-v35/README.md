# Actual reflected-receiver outcome diagnostic

The full Sun/underwater appearance goal remains unachieved.

This opt-in diagnostic changes only the packaged water fragment shader, not the
shipping source. Pure-TIR pixels are green for a world trace with paired source
readiness, yellow for known geometry without its source, blue for a screen-space
hit, red for a miss with an enabled field, and magenta for no attempted field
trace. Non-TIR pixels are gray. Subsequent composite/tone processing changes
displayed intensity: these are path labels, not raw radiance or exact hit counts.

Actual Aqualumen Lab / UUID-guarded AqualumenNaturalV2 captured 57 native PNGs.
Moving frame-015 was actually viewed: sparse green strips occur near the rim,
while broad exterior TIR regions are red. Thus at least some production world
receiver source paths are reached in this actual scene; the exterior is mostly
trace rejection, not merely a uniformly black material source. This single image
does not qualify all corners, motion, lifetime, trace distances or hit correctness.
It does not identify which rejection condition dominates.

Next diagnosis must distinguish interface interval rejection, field/range exit,
upward reflected directions and unknown geometry. Simply brightening fallback
scatter would conceal the observed miss rather than repair the transport.

The diagnostic builder has exclusive-output and unique-anchor tests and changes
no other archive entry in its CPU fixture. NVIDIA compiled/linked the diagnostic
pack; this receipt contains no standalone GPU behavior regression. Actual run
manifest and native motion audit remain separate runtime evidence.

Launcher exited normally (0). Normal configs, Mods, instance settings and
ordinary save hashes were restored exactly without save rollback. Receiver-only
stdout is preserved in `candidate-receiver-runtime.log`; private launcher log
content is excluded. The diagnostic pack is not an accepted normal rendering.
