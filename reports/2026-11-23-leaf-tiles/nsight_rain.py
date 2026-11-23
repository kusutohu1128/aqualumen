"""Collect OpenGL and long OS runtime calls from an already loaded private Minecraft world."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess as sp
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import ground_shadow_lab as lab


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wait_until(test, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if value := test():
            return value
        time.sleep(0.5)
    raise TimeoutError(test)


def snapshot(files):
    return {str(p): digest(p) for p in files if p.is_file()}


def collect(out, cage):
    receipt = json.loads(
        (HERE.parent / "2026-11-21-animal-light/woodland/rainy-oak-walk-r2/complete.json").read_text()
    )
    src = Path(receipt["privateGameDir"]).resolve()
    assert src.is_relative_to("/tmp") and not any(p.is_symlink() for p in src.rglob("*"))
    assert receipt["cleanExit"] and receipt["results"]["completed"] == ["cross-under-rainy-oak"]
    pack = src / "shaderpacks" / receipt["pack"]
    assert digest(pack) == receipt["packSha256"] == digest(ROOT / "dist" / pack.name)
    assert not lab.SENTINEL.exists()
    protected = list((src / "saves").rglob("*")) + list((lab.GAME / "mods").glob("*"))
    protected.extend(
        lab.GAME / p for p in ("config/iris.properties", "config/sodium-options.json", "options.txt")
    )
    baseline = snapshot(protected)
    base = Path(tempfile.mkdtemp(prefix="aql-nsight-wet-"))
    game = base / "minecraft"
    shutil.copytree(src, game, ignore=shutil.ignore_patterns("screenshots", "logs", "session.lock"))
    driver_cache = ROOT / "build/leaf-tiles" / ("nsight-glcache-" + receipt["packSha256"][:16])
    if not driver_cache.exists():
        shutil.copytree(
            ROOT / "build/animal-light/woodland/driver-cache" / receipt["packSha256"][:16], driver_cache
        )
    runtime = json.loads((HERE.parent / "2026-11-20-underwater-refinement/local-launch.json").read_text())
    (world,) = (game / "saves").iterdir()
    assert world.name == "Aqualumen-Oak-Night-Trail"
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
        "Woodwalker",
        "--version",
        "1.21.1",
        "--gameDir",
        str(game),
        "--assetsDir",
        str(lab.GAME.parents[2] / "assets"),
        "--assetIndex",
        "17",
        "--uuid",
        "00000000000040008000000000000308",
        "--accessToken",
        "0",
        "--userType",
        "legacy",
        "--width",
        "1600",
        "--height",
        "900",
        "--quickPlaySingleplayer",
        world.name,
    ]
    session = "aql-wet-" + base.name.rsplit("-", 1)[-1]
    xdisplay = os.environ.copy()
    for key in (
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "XAUTHORITY",
        "LD_PRELOAD",
        "JAVA_TOOL_OPTIONS",
        "JDK_JAVA_OPTIONS",
    ):
        xdisplay.pop(key, None)
    display_dir = base / "runtime"
    display_dir.mkdir(mode=0o700)
    server_env = dict(
        xdisplay,
        XDG_RUNTIME_DIR=str(display_dir),
        WLR_BACKENDS="headless",
        WLR_RENDERER="gles2",
        WLR_RENDER_DRM_DEVICE="/dev/dri/renderD128",
        WLR_LIBINPUT_NO_DEVICES="1",
        LD_LIBRARY_PATH=str(cage.parent.parent / "lib/x86_64-linux-gnu"),
    )
    endpoint = base / "private-display.json"
    # Cage gives its client the private Xwayland endpoint. Keep that client alive
    # while the capture controller starts and stops a separate Nsight session.
    publish_display = """
import json
import os
from pathlib import Path
import signal
import sys

endpoint = Path(sys.argv[1])
pending = endpoint.with_suffix(".tmp")
keys = ("DISPLAY", "XAUTHORITY", "WAYLAND_DISPLAY")
pending.write_text(json.dumps({key: os.environ[key] for key in keys if key in os.environ}))
pending.replace(endpoint)
signal.pause()
"""
    logfile = game / "logs/latest.log"

    def game_log():
        return logfile.read_text(errors="replace") if logfile.exists() else ""

    def joined():
        text = game_log()
        if ("OpenGL Renderer:" in text and receipt["renderer"] not in text) or "[VGL] ERROR:" in (
            out / "capture.log"
        ).read_text(errors="replace"):
            raise RuntimeError("private renderer could not initialize with Nsight")
        return "contact bridge initialized" in text and "logged in with entity id" in text

    def x(*args):
        return sp.run(
            ["xdotool", *args], env=xdisplay, capture_output=True, text=True, timeout=5
        ).stdout.strip()

    with (out / "capture.log").open("xb") as log:
        server = sp.Popen(
            [str(cage), "--", sys.executable, "-c", publish_display, str(endpoint)],
            env=server_env,
            stdout=log,
            stderr=log,
        )
        started = False

        def ns(*args, timeout=45):
            sp.run(["nsys", *args], stdout=log, stderr=log, timeout=timeout, check=True)

        try:
            wait_until(lambda: endpoint.exists() and server.poll() is None, 12)
            private = json.loads(endpoint.read_text())
            display = private["DISPLAY"]
            assert (
                display != os.environ.get("DISPLAY")
                and (display_dir / private["WAYLAND_DISPLAY"]).is_socket()
            )
            xdisplay["DISPLAY"] = display
            if "XAUTHORITY" in private:
                xdisplay["XAUTHORITY"] = private["XAUTHORITY"]
            env = dict(
                xdisplay,
                ALSOFT_DRIVERS="null",
                __GL_SHADER_DISK_CACHE_PATH=str(driver_cache),
                XDG_CACHE_HOME=str(base / "cache"),
            )
            sp.Popen(
                [
                    "nsys",
                    "launch",
                    "--session-new=" + session,
                    "--trace=opengl,osrt",
                    "--osrt-threshold=1000000",
                    "--opengl-gpu-workload=false",
                    *java,
                ],
                cwd=game,
                env=env,
                stdout=log,
                stderr=log,
            )
            started = True
            wait_until(joined, 900)
            time.sleep(4)
            wid = wait_until(lambda: x("search", "--onlyvisible", "--name", "Minecraft").splitlines(), 10)[-1]
            pid = int(x("getwindowpid", wid))
            proc = Path("/proc", str(pid))
            assert (proc / "cwd").resolve() == game and (proc / "exe").resolve() == Path(
                runtime["java"]
            ).resolve()
            assert str(game).encode() in (proc / "cmdline").read_bytes().split(b"\0")
            assert receipt["renderer"] in game_log() and "Using shaderpack: " + pack.name in game_log()
            geometry = x("getwindowgeometry", "--shell", wid)
            ns(
                "start",
                "--session=" + session,
                "--sample=none",
                "--cpuctxsw=none",
                "--output=" + str(out / "minecraft"),
            )
            time.sleep(6)
            ns("stop", "--session=" + session)
            assert x("getwindowpid", wid) == str(pid) and (proc / "cwd").resolve() == game
            sp.run(["/tmp/aqualumen-wm-close", hex(int(wid))], env=xdisplay, check=True, timeout=6)
            wait_until(lambda: "Saving worlds" in game_log() and not (proc / "exe").exists(), 55)
        finally:
            if started:
                sp.run(
                    ["nsys", "shutdown", "--session=" + session, "--kill=sigterm"],
                    stdout=log,
                    stderr=log,
                    timeout=25,
                )
            server.terminate()
            server.wait(timeout=10)
    assert (
        (out / "minecraft.nsys-rep").stat().st_size > 0
        and snapshot(protected) == baseline
        and not lab.SENTINEL.exists()
    )
    (out / "receipt.json").write_text(
        json.dumps(
            dict(
                javaPid=pid,
                packSHA=receipt["packSha256"],
                renderer=receipt["renderer"],
                game=str(game),
                sourceSaveAndLabChecksPassed=True,
                normalWorldSave=True,
                display=display,
                window=geometry,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    out = Path(sys.argv[1]).resolve()
    out.mkdir(exist_ok=False, parents=True)
    with open("/tmp/aql-render21-1000.lock", "a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        collect(out, Path(sys.argv[2]).resolve(strict=True))
