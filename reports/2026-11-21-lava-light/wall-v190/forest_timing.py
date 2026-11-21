"""Measure real Minecraft frames at the established daylight birch on a private X server."""

import argparse
import fcntl
import gzip
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[2]
runner_path = here.parent / "runtime-v190/run.py"
spec = importlib.util.spec_from_file_location("v190_private", runner_path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
g = runner.g
scenes = ["ground-noon", "ground-evening", "ground-low-sun"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pack", type=Path)
    p.add_argument("label")
    p.add_argument("--compiler-mod", type=Path)
    p.add_argument(
        "--driver-cache-seed",
        type=Path,
        default=Path.home() / ".cache/aqualumen-lab-shader-driver",
    )
    args = p.parse_args()
    assert args.label.replace("-", "").isalnum()
    pack = args.pack.resolve(strict=True)
    renderer_size = (2560, 1440)
    out = here / args.label
    out.mkdir()
    jar = root / "build/aqualumen-benchmark-forest-light.jar"
    reference = json.loads(
        (
            root / "reports/2026-11-21-leaf-light/timing-cone/capture/run.json"
        ).read_text()
    )
    assert reference["scenarios"] == scenes
    lab = g.GAME.resolve()
    original_world = lab / "saves" / g.lab.WORLD
    g.lab.shared.world_marker()
    source = runner.base.tree(original_world)
    protected = {
        n: g.lab.sha(lab / n)
        for n in ("config/iris.properties", "config/sodium-options.json", "options.txt")
    }
    runtime = json.loads(
        (
            root / "reports/2026-11-20-underwater-refinement/local-launch.json"
        ).read_text()
    )
    work = Path(tempfile.mkdtemp(prefix="aql-lava-timing-"))
    game = work / "Aqualumen Lab/minecraft"
    for folder in ("config", "mods", "shaderpacks", "saves"):
        (game / folder).mkdir(parents=True)
    with (original_world / "session.lock").open("r+b") as f:
        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runner.base.copy_world(original_world, game / "saves" / g.lab.WORLD)
    clone = game / "saves" / g.lab.WORLD
    assert (
        runner.base.tree(clone) == source
        and g.lab.pairs((clone / "aqualumen-world.properties").read_bytes())["world_id"]
        == g.lab.WORLD_ID
    )
    assert (
        runner.base.nbt(gzip.decompress((clone / "level.dat").read_bytes()))["Data"][
            "WorldGenSettings"
        ]["seed"]
        == 308060
    )
    for mod in g.lab.NORMAL_MODS:
        shutil.copy2(lab / "mods" / mod, game / "mods")
    compiler_digest = None
    if args.compiler_mod:
        companion = args.compiler_mod.resolve(strict=True)
        assert companion.name in ("aqualumen-lighting-compiler-0.1.0.jar", "aqualumen-lighting-compiler-0.2.1.jar", "aqualumen-lighting-compiler-0.3.0.jar")
        compiler_digest = g.lab.sha(Path(shutil.copy2(companion, game / "mods")))
    shutil.copy2(jar, game / "mods")
    shutil.copy2(pack, game / "shaderpacks")
    for cfg in ("iris.properties", "sodium-options.json"):
        shutil.copy2(lab / "config" / cfg, game / "config")
    iris = game / "config/iris.properties"
    iris.write_bytes(
        g.lab.replace_values(iris.read_bytes(), {"shaderPack": pack.name}, "=")
    )
    w, h = renderer_size
    settings = dict(
        g.lab.OPTIONS,
        maxFps="260",
        overrideWidth=str(w),
        overrideHeight=str(h),
        pauseOnLostFocus="false",
        enableVsync="false",
        fullscreen="false",
    )
    (game / "options.txt").write_bytes(
        g.lab.replace_values((lab / "options.txt").read_bytes(), settings, ":")
    )
    opt = game / "config/aqualumen-benchmark.enabled"
    req = game / "aqualumen-benchmark/request.properties"
    (game / "config/aqualumen-benchmark.properties").write_bytes(
        g.lab.properties(
            {
                "schema": 2,
                "world": g.lab.WORLD,
                "world_id": g.lab.WORLD_ID,
                "expected_pack": pack.name,
                "expected_pack_sha256": g.lab.sha(pack),
                "width": w,
                "height": h,
                "render_chunks": 12,
                "simulation_chunks": 6,
                "capture_motion": "false",
                "ground_frame_strip": "false",
                "water_frame_clip": "false",
            }
        )
    )
    runner.PRIVATE_DISPLAY_MIN = 221
    runner.SCREEN = renderer_size
    cache = root / "build/lava-light-study/timing-driver-caches" / g.lab.sha(pack)[:16]
    if not cache.exists():
        # Seed a private writable driver cache. A warm shader binary is keyed by
        # the linked program and driver, independently of the shader pack name.
        seed = args.driver_cache_seed
        if seed.is_dir():
            cache.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(seed, cache)
        else:
            cache.mkdir(parents=True)
    vgl = Path(runner.VGL_DIR_FILE.read_text().strip()) / "x/usr/lib"
    xvfb = None
    proc = None
    started = time.monotonic()
    # A timed pair owns the shared profiling lock for the complete session.
    with open(runner.base.LOCK, "a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            xvfb, display = runner.start_xvfb(work)
            env = runner.clean_env(display)
            env.update(
                ALSOFT_DRIVERS="null",
                VGL_DISPLAY="egl0",
                VGL_LOGO="0",
                VGL_SPOIL="0",
                VGL_COMPRESS="0",
                LD_PRELOAD=f"{vgl}/libdlfaker.so:{vgl}/libvglfaker.so",
                __GL_SHADER_DISK_CACHE_PATH=str(cache),
            )
            opt.write_text("Opt-in for this exact private birch frame timing run\n")
            java = [
                runtime["java"],
                "-Xms512m",
                "-Xmx2600m",
                "-XX:ActiveProcessorCount=4",
                "-Dorg.lwjgl.openal.libname=libopenal.so.1",
                "-cp",
                ":".join(runtime["cp"]),
                "net.fabricmc.loader.impl.launch.knot.KnotClient",
                "--username",
                "AqualumenOptics",
                "--version",
                "1.21.1",
                "--gameDir",
                str(game),
                "--assetsDir",
                str(lab.parents[2] / "assets"),
                "--assetIndex",
                "17",
                "--uuid",
                "00000000000040008000000000000411",
                "--accessToken",
                "0",
                "--userType",
                "legacy",
                "--width",
                str(w),
                "--height",
                str(h),
                "--quickPlaySingleplayer",
                g.lab.WORLD,
            ]
            (out / "private-game.txt").write_text(str(game))
            log = out / "client.log"
            control = game / "aqualumen-benchmark"
            asked = False
            focused = False
            run = "forest-" + args.label
            with log.open("xb") as sink:
                proc = subprocess.Popen(
                    java, cwd=game, stdout=sink, stderr=sink, env=env
                )
                deadline = time.monotonic() + 1500
                while proc.poll() is None:
                    text = log.read_text(errors="replace")
                    if not focused and "OpenGL Renderer:" in text:
                        wins = runner.window_ids(env, proc.pid)
                        if len(wins) == 1:
                            subprocess.run(
                                ["xdotool", "windowfocus", wins[0]],
                                env=env,
                                check=True,
                                timeout=6,
                            )
                            focused = True
                    if (
                        not asked
                        and "logged in with entity id" in text
                        and (control / "status.json").exists()
                        and "Started "
                        in text.split(
                            "Creating pipeline for dimension minecraft:overworld"
                        )[-1]
                        and "worker threads"
                        in text.split(
                            "Creating pipeline for dimension minecraft:overworld"
                        )[-1]
                    ):
                        subprocess.run(
                            [
                                sys.executable,
                                str(root / "tools/benchmark-control.py"),
                                "--game",
                                str(game),
                                "start",
                                "--run-id",
                                run,
                                "--scenes",
                                *scenes,
                                "--warmup",
                                "15",
                                "--sample",
                                "10",
                                "--auto-quit",
                            ],
                            check=True,
                        )
                        asked = True
                        deadline = time.monotonic() + 260
                    assert (
                        time.monotonic() < deadline
                        and "Benchmark aborted:" not in text
                        and "reverting to default" not in text.lower()
                        and "Error encountered when linking program" not in text
                        and "assembly compile error" not in text
                    )
                    time.sleep(0.4)
            assert proc.returncode == 0 and asked
            if compiler_digest:
                assert "Compiling Aqualumen area lighting with NVIDIA function calls" in log.read_text()
            stored = control / "runs" / run
            state = json.loads((stored / "run.json").read_text())
            assert (
                state["shader_active"]
                and not state["shader_fallback"]
                and state["pack_sha256"] == g.lab.sha(pack)
            )
            assert (
                state["world_id"] == g.lab.WORLD_ID
                and "RTX 3080 Ti" in state["gl_renderer"]
            )
            assert (
                state["framebuffer_resolution"] == list(renderer_size)
                and state["scenarios"] == scenes
            )
            assert (
                json.loads((stored / "complete.json").read_text())["status"]
                == "complete"
            )
            shutil.copytree(stored, out / "capture")
            rows = {}
            for name, mode in zip(scenes, ("off", "warm", "soul"), strict=True):
                d = json.loads((stored / (name + ".json")).read_text())
                assert (
                    d["frames"] > 0
                    and d["camera_follows_local_player"]
                    and d["framebuffer_resolution"] == list(renderer_size)
                )
                rows[mode] = {k: d[k] for k in ("frames", "mean_fps", "p99_ms")}
            assert runner.base.tree(original_world) == source and all(
                g.lab.sha(lab / n) == v for n, v in protected.items()
            )
            (out / "timing.json").write_text(
                json.dumps(
                    {
                        "pack": pack.name,
                        "sha256": state["pack_sha256"],
                        "renderer": state["gl_renderer"],
                        "framebuffer": renderer_size,
                        "scope": "Real Minecraft render frames. Private VirtualGL/Xvfb presentation path. May incur extra copies relative to the desktop.",
                        "samples": rows,
                        "runtimeSeconds": time.monotonic() - started,
                        "driverCacheSeed": str(args.driver_cache_seed),
                        "compilerModSha256": compiler_digest,
                        "worldAndConfigUnchanged": True,
                    },
                    indent=2,
                )
                + "\n"
            )
        finally:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            if xvfb and xvfb.poll() is None:
                xvfb.terminate()
                xvfb.wait(timeout=10)
            opt.unlink(missing_ok=True)
            req.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
