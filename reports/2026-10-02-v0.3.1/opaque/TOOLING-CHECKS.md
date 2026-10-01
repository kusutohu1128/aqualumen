# Instrumentation and evidence checks

Run `opacity-v0.3.1-8` completed on 2026-10-02 00:23:39 JST
(2026-10-01 15:23:39 UTC). This is an artificial near/far wall-occlusion
positive-control run, not the separate causal cloud-radiance regression.

Before runtime, `bash tools/build-benchmark-mod.sh` passed both CPU-only tests:

- `FinisherWaitTest`: wait for client dimension/camera/player transition,
  enforce the 60 s timeout and retain the strict integrated-server guard.
- `OcclusionFixtureTest`: exact eight variants and approved 130-cell plots,
  identical geometry and two fixed lights across color pairs, 47 changed
  target-color cells, dedicated name+UUID authorization, exact-state-only
  cleanup decisions, and measured first-person eye/camera match rejection.

These tests exercise instrumentation logic, not a CPU clone of the renderer.
The installed benchmark JAR was pinned by root to SHA-256
`c8ccb66ef30d4c5aa86ef0e5e75733c3724a92971c019fc3ebe342ef57c4c400`;
its `Recorder.class` SHA-256 is
`b9d7289ef423cd6436255439898e523459f69b5eb9aece7118a69cd399f410a2`.
No source JAR rebuild or setting change occurred during timed captures.

`python3 tools/report.py RUN_DIRECTORY` independently recomputed all eight
CSV rows: 20,623 intervals, maximum 8.113650 ms, zero >16.667 ms intervals.
The recorded frame-limit value is **260**; these are wall-clock measurements
under that configuration, not a claim of unbounded GPU throughput or a
universal 60 FPS guarantee. Shader pack SHA-256 was
`d32ce1763e7b48573c544dba9ae476ea2bf910725cbf365140140a1d1708e856`.

Every capture recorded first-person perspective and camera/eye error
0.00000011920928955078125 m, well below the 0.05 m bound. The local UUID player
was `bfdaa1e1-f633-3ba5-8a85-a66cf04a73ee`; actual eye was
`(448.5, 161.62000000476837, -383.5)` and actual Camera position
`(448.5, 161.61999988555908, -383.5)`.

All eight fixture-cleanup records report `cleaned-to-air`, no preserved
conflicts and `cleanup_complete=true`; `complete.json` confirms final cleanup.
No control ownership journal remained. All 67 original run/report files were
copied and their SHA-256 values independently matched the source directory.
This additional tooling note is not part of those original 67 files.

Near/far open magenta/lime targets are visibly distinct, while the solid-wall
shots hide them. Clouds and exposure evolve between shots, so their sequential
pixel differences alone cannot establish the causal cloud-ghosting fix.
