# Stack profiling v45 — recording failed, no hotspot conclusion

The v52 Minecraft experiment completed its static and moving scenes and
auto-quit. The owned launcher exited zero; native-motion audit verified 32
PNGs. Exact normal configuration/Mods and unchanged ordinary-save hashes were
verified after restoration. This is not visual or performance acceptance.

No JFR recording was produced. Do not infer a hotspot from this run.

The first attach guard correctly refused a assumed `--quickPlaySingleplayer`
argument: Prism uses a wrapper and this JVM's command line has no such flags.
The owned executable and isolated-game cwd can instead be verified by inode,
alongside the live exact benchmark run ID and disposable-world UUID.

JFR.start subsequently reported that the repository JFC was inaccessible in
the Flatpak namespace. An exact temporary copy inside the owned benchmark
directory was accessible, but the diagnostic-command parser split its path
at the space in `Aqualumen Lab`. Passing a subprocess argv element is not
sufficient to quote a JFR option for that parser. The final guarded attempt
found Java already stopped and did not restart it or attach elsewhere.

The temporary JFC was removed only after Java stopped and its bytes matched
the source. The minimal source JFC enables only execution/native-method and
allocation samples, not environment/system-property/JVM-argument events.

Next recording needs target-visible paths and diagnostic-parser quotation,
started immediately after the owned benchmark request. Validate those details
before spending another complete experiment. This failure does not justify
removing ownership or fresh-geometry checks to improve throughput.
