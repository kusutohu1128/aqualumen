# Aqualumen

Original Minecraft Iris shader pack focused on water and sunlight. RTX 3080 Ti, 2560x1440, 12 chunks. The stable release is 1.8.0; 1.9.0 previews and experimental layers build on top of it. Visual quality takes priority over a strict 60 FPS floor; report frame timings honestly without treating that old budget as the release gate.

- `shaders/` is the development tree (`make check-development`); `release/shaders/` is the normal-play 1.8.0 tree. `release/<variant>/` directories are overlay layers that `tools/build.py` flags stack (each experimental flag includes its predecessors), packed by `tools/release_pack.py`. GLSL sources live under each tree's `shaders/`, shared physical models under `lib/`.
- `python3 tools/build.py` makes an installable ZIP in `dist/`.
- `make check` compiles/links the `release/shaders` program pairs (`--play-release`) plus the rain-shelter probe; per-feature targets include `check-lava`, `check-canopy`, `check-ground`, `check-animal`, `check-ceiling`, `check-eye` and `check-face`. Requires EGL and libepoxy development files.
- Record the GL renderer so software results cannot be mistaken for NVIDIA results. Follow current tool permissions for GPU access.
- GitHub CI runs `make check` on Mesa llvmpipe (software rendering) with `AQUALUMEN_SOFTWARE_GL=1`, which skips the two NVIDIA-only probes and one compile-strictness case; its results are not NVIDIA results and a green CI is not a substitute for an NVIDIA run.
- `physics-mod/` contains the read-only client contact bridge, pinned to Iris 1.8.8 / Minecraft 1.21.1. Build via `tools/build-physics-mod.sh`.
- `compiler-mod/` is the lighting compiler 0.3.0 that the area-light previews require. Build via `bash tools/build-lighting-compiler.sh`.
- Persistent interaction waves use `begin.csh`/`begin1.csh` (and `setup.csh`) under `shaders/` and `release/shaders/`; check CFL, image barriers and camera-relative coordinates when editing.
- Raw GPU readbacks and captures under `reports/` are gitignored but kept on disk when a tracked report references them; `build/` likewise holds outputs referenced by reports — do not bulk-delete either.
- Benchmark automation is opt-in and exact-world UUID guarded; never enable it for ordinary user worlds.
- Preserve existing Minecraft instances, configs and worlds. Only install to the separate `Aqualumen Lab` instance.
- Distinguish analytical/approximate rendering, actual fluid simulation, GPU harness timings and Minecraft frame timings in reports.
- No purchased assets or copied shader-pack sources. Cite algorithm references in README.
