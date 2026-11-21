# Receiver JFR v46 — measured hotspot evidence, not accepted

A host smoke process first verified diagnostic-parser quotation with spaces in
both JFC and output paths. The actual isolated Minecraft/NVIDIA process was
then checked by executable and cwd inode, exact live benchmark run ID and
disposable-world UUID. A target-visible JFC started a confirmed 40-second JFR.
The raw recording is archived with mode 0600. It is not a performance acceptance
run: recording adds overhead, and both ordinary tests still run around 0.8 FPS.

`stack-summary.json` was generated from execution/native/allocation events using
`jfr print --json --stack-depth 128`. JVM class names were normalized from slash
to dot before checking owned frames. The initial shallow-stack, mixed-name
summary undercounted owned work and was replaced; do not use that first analysis.

There are 1855 render-thread execution/native samples, of which 1784 contain
the physics bridge. Exclusive sampled leaves include HashMap.getNode (457),
HashMap.resize (106), HashMap.get (80), and HashMap.putVal (51), alongside
reflection access/dispatch. Inclusive counts overlap and cannot be summed as
exclusive CPU time. No exact GPU or per-method wall duration is inferred.

Allocation sampling estimates approximately 12.2 GB of Object[] and 3.0 GB of
coordinate Top objects during the recording. The first owned allocation caller
LoadedReceiverWorld.receiverCell accounts for approximately 12.4 GB of estimated
allocation weight. These are weighted samples, not exact heap/retained sizes.
Both per-cell reflection argument arrays and cache machinery merit optimization;
removing guards or skipping fresh geometry is not justified.

One causal next change was made: Top now mixes each coordinate independently
before hash-map lookup, with unchanged record equality. The old polynomial
spatial hash collapses the 87×36×87 lattice to 83818 distinct hashes (up to six
cells per hash). CPU verification now reports 272480 distinct hashes for 272484
actual-window keys, checks every lookup with a newly constructed equal key,
and checks extreme integer coordinates. This distribution result is not a
runtime speedup. Related source/run-radiance tests pass; Mod v53 built, SHA256
`ddf8326e8bb4f22b77374d4f6f3b65a3432c913feb7ac0e2fd95477cf7ce1701`,
but has not been installed or visually accepted.

The v46 benchmark completed static and moving scenes, launcher exited zero,
and native-motion audit verified 33 PNGs. No full image review was performed
in this profiling turn. Normal configuration/Mods are restored exactly and
ordinary-save hashes are unchanged without rollback. Owned temporary JFC/JFR
files were removed only after Java stopped and archive/source bytes matched.
The complete Sun, underwater-window appearance and performance goal remains open.
