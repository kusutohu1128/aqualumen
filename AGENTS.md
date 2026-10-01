# Aqualumen

Original Minecraft Iris shader pack focused on water and sunlight. Target: RTX 3080 Ti, 2560x1440, 12 chunks, 60 FPS (16.67 ms); a target is not a measured result.

- GLSL sources live under `shaders/`; shared physical models under `shaders/lib/`.
- `python3 tools/build.py` makes an installable ZIP in `dist/`.
- `make check` compiles/links all program pairs on an OpenGL compatibility context. Requires EGL and libepoxy development files.
- GPU checks outside the sandbox need permission. Record the GL renderer so software results cannot be mistaken for NVIDIA results.
- Preserve existing Minecraft instances, configs and worlds. Only install to the separate `Aqualumen Lab` instance.
- Distinguish analytical/approximate rendering, actual fluid simulation, GPU harness timings and Minecraft frame timings in reports.
- No purchased assets or copied shader-pack sources. Cite algorithm references in README.
