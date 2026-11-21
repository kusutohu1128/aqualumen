# runtime-v190: guarded real-game runner on a private display

```
./setup-vgl.sh                      # user-local VirtualGL 3.1.5 (public .deb, sha256 checked) -> /tmp/aql-v190-vgl-XXXX, records vgl-dir.txt
python3 run.py <pack.zip> <label> [--set core|all | --stages a,b] [--backend vgl|llvmpipe] [--load-timeout S]
python3 analyze.py <label> [<other-label>]      # ROI luminance, delta vs dark, restoration exactness, x11-vs-F2
python3 linktime.py <unzipped-shaders> out.json # build/glcheck --compile-only per-program timing on NVIDIA (holds render lock)
```
* `run.py` starts its own Xvfb (display >= :171, refuses :0/:1/$DISPLAY), clones the exact V2 world (UUID/seed checked, session.lock),
  copies only the three normal mods + Lab options/Iris/Sodium configs, launches under VirtualGL (`VGL_DISPLAY=egl0`) and holds
  `/tmp/aql-render21-1000.lock` (waits <= 900 s, never forces). Original world/configs are hashed before/after.
* `scene.py`: roofed chamber (basin.py), white wall z=366, 3x3 lava pool flush at y=172, stone pillar (202,173..175,364),
  torch (200,173,363), soul torch (204,173,365). Every stage re-assigns all 14 mutable cells; the datapack verifies cells, roof/wall samples,
  time=18000, scoreboard stage index, pose/rotation, entity-free room at READY (40 t) and again at STILL (170 t); frames count only if
  READY..STILL has no BEGIN/DRIFT/FAIL. Frames per stage: x11grab, game-side F2, x11grab.
* Do not run two runners at once (world session.lock race). llvmpipe stage capture is untested with the retrying `f` arm (earlier stall was a lost first keypress, not slow frames).
