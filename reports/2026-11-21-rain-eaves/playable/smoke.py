"""Native route smoke of dist/Aqualumen-Rain-Walk.zip: ordinary Iris + Sodium + Aqualumen physics, WASD only.

    python3 -I smoke.py [--pack build/Aqualumen-1.7.0-rain-rc1.zip] [--out smoke-rc1] [--cache <dir>]

* The world is unzipped from the delivered archive into a disposable game dir under /tmp.  No Lab instance, user
  world, benchmark mod or sentinel file is touched; only read-copies of the three normal mods, options and Iris/Sodium
  config are taken from the Lab, exactly like the Lantern House smoke.
* The shared render lock /tmp/aql-render21-1000.lock is taken (blocking) before launch and held until the client exits.
* Input is keyboard only (hold W out, hold S back) sent with xdotool to the private window; before every key press the
  window found by the exact client PID must have X input focus.  There are no mouse clicks and no mouse moves.
* The route is the straight line x = 3.5 from the spawn (feet z 12.5) to the pond bank; both directions use the same
  hold times.  This is a route smoke of a few minutes, NOT a long-run acceptance.
"""

import argparse
import fcntl
import gzip
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LOCK = "/tmp/aql-render21-1000.lock"
WORLD_ZIP = ROOT / "dist/Aqualumen-Rain-Walk.zip"
WORLD = "Aqualumen-Rain-Walk"
W, H = 1600, 900
SPEED = 4.317  # blocks per second, vanilla walking
SPAWN_Z = 12.5

# (label, feet z to reach, screenshot name) ; reached by holding W for (previous z - z) / SPEED seconds
STATIONS = [
    ("under-eave", 2.0, "02-under-eave.png"),
    ("torch-oak", -6.0, "03-torch-oak.png"),
    ("south-portal", -31.0, "04-south-portal.png"),
    ("tunnel-mid", -43.0, "05-tunnel-mid.png"),
    ("tunnel-north", -51.0, "05b-tunnel-north.png"),
    ("north-exit", -60.0, "06-north-exit.png"),
    ("pond-bank", -75.5, "07-pond-bank.png"),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def require(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default=str(ROOT / "build/Aqualumen-1.7.0-rain-rc3.zip"))
    ap.add_argument("--pack-sha", default="2c81439353053f7adb12700eb3fb4ea9b9991169ee165a7963e182e9cb0ab4d9",
                    help="expected SHA-256 of the pack (parent's final candidate rc3); empty string skips the check")
    ap.add_argument("--out", default="smoke-rc3")
    ap.add_argument("--no-f3", action="store_true", help="skip the F3 coordinate screenshots")
    ap.add_argument("--cache", default=None, help="persistent XDG cache dir (a warm NVIDIA shader cache shortens the pipeline build)")
    ap.add_argument("--stations", default=",".join(s[0] for s in STATIONS), help="comma list of stations to stop at on the way out")
    args = ap.parse_args()
    pack = Path(args.pack).resolve()
    out = HERE / args.out
    require(os.getuid() == 1000, "uid")
    require(pack.is_file() and pack.suffix == ".zip", "pack missing")
    require(not out.exists(), "output dir exists")
    require(os.access("/tmp/aqualumen-wm-close", os.X_OK), "missing window-close helper")
    sys.path.insert(0, str(ROOT / ".audit"))
    sys.path.insert(0, str(ROOT / "tools"))
    import land_shadow_runtime_2026_10_23 as lab  # read-only helpers (paths, option editing)

    vw = load("aql_rw_validate", HERE / "validate_world.py")
    parse_nbt = vw.V.parse_nbt
    orig = lab.GAME.resolve()
    runtime = json.loads((ROOT / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
    assets = orig.parents[2] / "assets"
    guarded = {n: sha((orig / n).read_bytes()) for n in ("options.txt", "config/iris.properties", "config/sodium-options.json") if (orig / n).is_file()}
    mods = {n: sha((orig / "mods" / n).read_bytes()) for n in sorted(lab.NORMAL_MODS)}
    world_zip_sha, pack_sha = sha(WORLD_ZIP.read_bytes()), sha(pack.read_bytes())
    require(not args.pack_sha or pack_sha == args.pack_sha, "pack SHA-256 differs from the expected one: " + pack_sha)
    stations = [s for s in STATIONS if s[0] in args.stations.split(",")]

    out.mkdir()
    log = out / "client.log"
    print("waiting for render lock ...", flush=True)
    lock = open(LOCK, "a+b")
    fcntl.flock(lock, fcntl.LOCK_EX)
    t_lock = time.strftime("%H:%M:%S")
    print("lock acquired", t_lock, flush=True)

    root = Path(tempfile.mkdtemp(prefix="aql-rainwalk-smoke-", dir="/tmp"))
    game = root / "game"
    for n in ("mods", "config", "shaderpacks", "saves"):
        (game / n).mkdir(parents=True)
    for n in sorted(lab.NORMAL_MODS):
        shutil.copy(orig / "mods" / n, game / "mods")
    require({p.name for p in (game / "mods").iterdir()} == lab.NORMAL_MODS, "mods")
    shutil.copy(pack, game / "shaderpacks")
    for n in ("sodium-options.json", "iris.properties"):
        if (orig / "config" / n).exists():
            shutil.copy(orig / "config" / n, game / "config")
    iris = game / "config/iris.properties"
    iris.write_bytes(lab.replace_values(iris.read_bytes(), {"shaderPack": pack.name}, "="))
    options = dict(lab.OPTIONS, maxFps="120", overrideWidth=str(W), overrideHeight=str(H), pauseOnLostFocus="false", fullscreen="false")
    (game / "options.txt").write_bytes(lab.replace_values((orig / "options.txt").read_bytes(), options, ":"))
    with zipfile.ZipFile(WORLD_ZIP) as z:
        z.extractall(game / "saves")
    saved = game / "saves" / WORLD
    require((saved / "level.dat").is_file() and not (saved / "datapacks").exists(), "world unzip")
    (out / "private-game.txt").write_text(str(game) + "\n")
    cache = Path(args.cache) if args.cache else root / "cache"
    cache.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ, DISPLAY=":1", XDG_RUNTIME_DIR="/run/user/1000", DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus",
               __GLX_VENDOR_LIBRARY_NAME="nvidia", ALSOFT_DRIVERS="null", XDG_CACHE_HOME=str(cache))
    for k in ["JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "GALLIUM_DRIVER", "LIBGL_KOPPER_DRI2", "VK_DRIVER_FILES"]:
        env.pop(k, None)
    java = [runtime["java"], "-Xms512m", "-Xmx2600m", "-XX:ActiveProcessorCount=4", "-Dorg.lwjgl.openal.libname=libopenal.so.1", "-cp",
            ":".join(runtime["cp"]), "net.fabricmc.loader.impl.launch.knot.KnotClient", "--username", "RainWalker", "--version", "1.21.1",
            "--gameDir", str(game), "--assetsDir", str(assets), "--assetIndex", "17", "--uuid", "00000000000040008000000000000433",
            "--accessToken", "0", "--userType", "legacy", "--width", str(W), "--height", str(H), "--quickPlaySingleplayer", WORLD]
    steps, notes, keylog = [], [], []
    p = None
    t0 = [None]

    def text():
        return log.read_text(errors="replace")

    def x(*a, check=True, timeout=6):
        return subprocess.run(list(a), env=env, text=True, capture_output=True, check=check, timeout=timeout).stdout.strip()

    def window():
        r = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid", str(p.pid), "--name", "Minecraft"], env=env, text=True, capture_output=True)
        return r.stdout.strip() if r.returncode == 0 and len(r.stdout.split()) == 1 else None

    def since():
        return round(time.monotonic() - t0[0], 1)

    def grab(wid, name):
        f = out / name
        x("ffmpeg", "-v", "error", "-n", "-f", "x11grab", "-window_id", wid, "-i", ":1", "-frames:v", "1", "-threads", "1", str(f))
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], env=env, capture_output=True, check=True).stdout
        n = len(raw) // 3
        mean = [round(sum(raw[c::3]) / n, 2) for c in range(3)]
        spread = max(raw[::97]) - min(raw[::97])
        steps.append(dict(file=name, tAfterJoinS=since(), mean=mean, spread=spread, sha256=sha(f.read_bytes())))
        require(spread > 60, "frame looks uniform: " + name)

    def focused(wid):
        x("xdotool", "windowfocus", "--sync", wid)
        return x("xdotool", "getwindowfocus") == wid

    def f3_shot(wid, name):
        """Keyboard-only: F3 on, screenshot (XYZ readout), F3 off.  Position is read from the image afterwards."""
        if args.no_f3:
            return
        require(window() == wid and focused(wid), "private window lost focus; no F3 sent")
        x("xdotool", "key", "F3")
        time.sleep(1.0)
        grab(wid, name)
        require(focused(wid), "private window lost focus; F3 not toggled back")
        x("xdotool", "key", "F3")
        time.sleep(0.6)

    def hold(wid, key, seconds, label):
        require(window() == wid, "private window (exact PID) changed or vanished")
        require(focused(wid), "private window lost focus; no input sent")
        start = time.monotonic()
        x("xdotool", "keydown", key)
        try:
            while time.monotonic() - start < seconds:
                time.sleep(0.05)
        finally:
            x("xdotool", "keyup", key, check=False)
        keylog.append(dict(key=key, seconds=round(time.monotonic() - start, 2), label=label, tAfterJoinS=since()))

    with log.open("xb") as stream:
        p = subprocess.Popen(java, stdout=stream, stderr=stream, env=env, cwd=game)
        try:
            deadline = time.monotonic() + 300
            while "logged in with entity id" not in text():
                require(p.poll() is None and time.monotonic() < deadline, "never joined the world")
                time.sleep(0.5)
            t0[0] = time.monotonic()
            t = text()
            renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t)
            require(renderer and lab.nvidia(renderer.group(1)), "not the NVIDIA renderer")
            require("Using shaderpack: " + pack.name in t, "Iris did not select the pack")
            deadline = time.monotonic() + 420
            while not re.search(r"\[Aqualumen Physics\] .*bridge initialized", text()):
                require(p.poll() is None and time.monotonic() < deadline, "pipeline never finished")
                time.sleep(1)
            steps.append(dict(pipelineReadySecondsAfterJoin=since()))
            time.sleep(8)  # let the first chunks mesh
            wid = window()
            require(wid, "private window not found")
            grab(wid, "01-spawn.png")
            time.sleep(1.0)
            grab(wid, "01-spawn-b.png")
            f3_shot(wid, "f3-00-spawn.png")
            z = SPAWN_Z
            for label, target, shot in stations:  # out: W only
                hold(wid, "w", (z - target) / SPEED, "out:" + label)
                z = target
                time.sleep(1.2)
                grab(wid, shot)
                f3_shot(wid, "f3-" + shot)
            time.sleep(1.0)
            z = stations[-1][1]
            for label, target, shot in reversed(stations[:-1]):  # back: S only, same hold times
                hold(wid, "s", (target - z) / SPEED, "back:" + label)
                z = target
                time.sleep(1.2)
                grab(wid, "b-" + shot)
                f3_shot(wid, "f3-b-" + shot)
            hold(wid, "s", (SPAWN_Z - z) / SPEED, "back:spawn")
            time.sleep(1.5)
            grab(wid, "08-back-at-patio.png")
            f3_shot(wid, "f3-08-back-at-patio.png")
            # stay on the patio (no input) and watch the vanilla weather cycle end the rain (rainTime 3600 ticks = 180 s)
            for secs, name in ((168, "09-patio-t168-raining.png"), (200, "10-patio-t200-cleared.png"), (260, "11-patio-t260-dusk.png")):
                while since() < secs:
                    require(p.poll() is None, "client exited early")
                    time.sleep(0.5)
                grab(wid, name)
        finally:
            w = window() if p.poll() is None else None
            if w:
                subprocess.run(["/tmp/aqualumen-wm-close", hex(int(w))], check=False, env=env)
            try:
                p.wait(timeout=40)
            except subprocess.TimeoutExpired:
                p.terminate()
                p.wait(timeout=10)
    t = text()
    renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t).group(1).strip()
    errors = [l for l in t.splitlines() if re.search(r"/(ERROR|FATAL)\]|Exception|Failed to (load|read)|Couldn't", l)]
    (out / "log-errors.txt").write_text("\n".join(errors) + "\n")
    lvl = parse_nbt(gzip.decompress((saved / "level.dat").read_bytes()))["Data"]
    pfiles = sorted((saved / "playerdata").glob("*.dat")) if (saved / "playerdata").exists() else []
    pdat = parse_nbt(gzip.decompress(pfiles[0].read_bytes())) if pfiles else lvl.get("Player")
    result = dict(
        when=time.strftime("%Y-%m-%dT%H:%M:%S%z"), lockAcquired=t_lock, renderer=renderer,
        glVersion=next((m.group(1).strip() for m in re.finditer(r"OpenGL Version: ([^\n]+)", t)), None),
        pack=pack.name, packSha256=pack_sha, worldZip=WORLD_ZIP.name, worldZipSha256=world_zip_sha,
        persistentCache=bool(args.cache), gameDir=str(game), joinedLine=next(l for l in t.splitlines() if "logged in with entity id" in l),
        cleanShutdown="All dimensions are saved" in t, shaderFallback="Using shaderpack: " + pack.name not in t,
        modsLoaded=sorted(mods), steps=steps, keys=keylog, notes=notes, logErrors=errors[:20], logErrorCount=len(errors),
        input="keyboard only: xdotool keydown/keyup w and s; exact-PID window focus checked before each; no mouse clicks or moves",
        savedPlayerPos=pdat["Pos"] if pdat else None, savedPlayerRotation=pdat["Rotation"] if pdat else None,
        savedPlayerGameType=pdat.get("playerGameType") if pdat else None,
        savedLevel=dict(Time=lvl["Time"], DayTime=lvl["DayTime"], raining=lvl["raining"], rainTime=lvl["rainTime"], thundering=lvl["thundering"],
                        thunderTime=lvl["thunderTime"], clearWeatherTime=lvl["clearWeatherTime"], Difficulty=lvl["Difficulty"], GameType=lvl["GameType"],
                        allowCommands=lvl["allowCommands"], GameRules=lvl["GameRules"]),
        savedPlayerdataFiles=[p.name for p in pfiles],
        labFilesUnchanged={n: sha((orig / n).read_bytes()) == h for n, h in guarded.items()},
        modsUnchanged={n: sha((orig / "mods" / n).read_bytes()) == h for n, h in mods.items()},
        deliveredZipUnchanged=sha(WORLD_ZIP.read_bytes()) == world_zip_sha, packUnchanged=sha(pack.read_bytes()) == pack_sha,
    )
    require(all(result["labFilesUnchanged"].values()), "Lab config changed?!")
    (out / "smoke.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: result[k] for k in ("renderer", "cleanShutdown", "shaderFallback", "logErrorCount", "savedPlayerPos", "savedLevel")}, indent=1))


if __name__ == "__main__":
    main()
