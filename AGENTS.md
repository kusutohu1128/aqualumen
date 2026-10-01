# Aqualumen

Original Minecraft Iris shader pack focused on water and sunlight. Target: RTX 3080 Ti, 2560x1440, 12 chunks, 60 FPS (16.67 ms); a target is not a measured result.

- GLSL sources live under `shaders/`; shared physical models under `shaders/lib/`.
- `python3 tools/build.py` makes an installable ZIP in `dist/`.
- `make check` compiles/links all program pairs on an OpenGL compatibility context. Requires EGL and libepoxy development files.
- Record the GL renderer so software results cannot be mistaken for NVIDIA results. Follow current tool permissions for GPU access.
- `physics-mod/` contains the read-only client contact bridge, pinned to Iris 1.8.8 / Minecraft 1.21.1. Build via `tools/build-physics-mod.sh`.
- Persistent interaction waves use `setup/begin/begin1.csh`; check CFL, image barriers and camera-relative coordinates when editing.
- Benchmark automation is opt-in and exact-world UUID guarded; never enable it for ordinary user worlds.
- Preserve existing Minecraft instances, configs and worlds. Only install to the separate `Aqualumen Lab` instance.
- Distinguish analytical/approximate rendering, actual fluid simulation, GPU harness timings and Minecraft frame timings in reports.
- No purchased assets or copied shader-pack sources. Cite algorithm references in README.
