"""One private native smoke of dist/Aqualumen-Lantern-House.zip with the ordinary Aqualumen 1.6.0 pack.

    python3 -I smoke.py            # takes the shared render lock (blocks until free), launches ONE client

* The world is unzipped from the delivered archive into a disposable game dir under /tmp; no Lab, no
  existing save and no recorder mod is touched (only read-copies of the three normal mods and options).
* No datapack/commands: after the spawn frame, the *player's own keys* (hold W, one right click) are sent
  to the private window to open the front door and walk in -- exactly what a user does.  Every input
  step first checks that the private window has focus / is under the pointer.
* The client is closed with the window manager close helper; nothing stays open.
"""

import fcntl
import gzip
import hashlib
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
OUT = HERE / "smoke"  # attempt 1 was kept as smoke-attempt1 (client was still compiling shaders)
LOCK = "/tmp/aql-render21-1000.lock"
WORLD_ZIP = ROOT / "dist/Aqualumen-Lantern-House.zip"
PACK = ROOT / "dist/Aqualumen-1.6.0.zip"
PACK_SHA = "0b1843fd4172f80a2ffa3ce885974119b6c4b04b83a43f236bee96001be80a5e"
WORLD = "Aqualumen-Lantern-House"
W, H = 1600, 900


def sha(b):
    return hashlib.sha256(b).hexdigest()


def require(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def main():
    require(os.getuid() == 1000, "uid")
    require(sha(PACK.read_bytes()) == PACK_SHA, "ordinary 1.6.0 archive hash differs")
    require(not OUT.exists(), "smoke/ already exists")
    for h in ("/tmp/aqualumen-wm-close",):
        require(os.access(h, os.X_OK), "missing helper " + h)
    sys.path.insert(0, str(ROOT / ".audit"))
    sys.path.insert(0, str(ROOT / "tools"))
    import land_shadow_runtime_2026_10_23 as lab  # read-only helpers (paths, option editing)

    orig = lab.GAME.resolve()
    runtime = json.loads((ROOT / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
    assets = orig.parents[2] / "assets"
    guarded = {n: sha((orig / n).read_bytes()) for n in ("options.txt", "config/iris.properties", "config/sodium-options.json")
               if (orig / n).is_file()}
    mods = {n: sha((orig / "mods" / n).read_bytes()) for n in sorted(lab.NORMAL_MODS)}
    world_zip_sha = sha(WORLD_ZIP.read_bytes())

    OUT.mkdir()
    log = OUT / "client.log"
    print("waiting for render lock ...", flush=True)
    lock = open(LOCK, "a+b")
    fcntl.flock(lock, fcntl.LOCK_EX)
    t_lock = time.strftime("%H:%M:%S")
    print("lock acquired", t_lock, flush=True)

    root = Path(tempfile.mkdtemp(prefix="aql-lantern-smoke-", dir="/tmp"))
    game = root / "game"
    for n in ("mods", "config", "shaderpacks", "saves"):
        (game / n).mkdir(parents=True)
    for n in sorted(lab.NORMAL_MODS):
        shutil.copy(orig / "mods" / n, game / "mods")
    require({p.name for p in (game / "mods").iterdir()} == lab.NORMAL_MODS, "mods")
    shutil.copy(PACK, game / "shaderpacks")
    for n in ("sodium-options.json", "iris.properties"):
        if (orig / "config" / n).exists():
            shutil.copy(orig / "config" / n, game / "config")
    iris = game / "config/iris.properties"
    iris.write_bytes(lab.replace_values(iris.read_bytes(), {"shaderPack": PACK.name}, "="))
    options = dict(lab.OPTIONS, maxFps="120", overrideWidth=str(W), overrideHeight=str(H), pauseOnLostFocus="false",
                   fullscreen="false")
    (game / "options.txt").write_bytes(lab.replace_values((orig / "options.txt").read_bytes(), options, ":"))
    with zipfile.ZipFile(WORLD_ZIP) as z:
        z.extractall(game / "saves")  # top-level folder = the world
    saved = game / "saves" / WORLD
    require((saved / "level.dat").is_file() and not (saved / "datapacks").exists(), "world unzip")
    (OUT / "private-game.txt").write_text(str(game) + "\n")

    env = dict(os.environ, DISPLAY=":1", XDG_RUNTIME_DIR="/run/user/1000",
               DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus", __GLX_VENDOR_LIBRARY_NAME="nvidia",
               ALSOFT_DRIVERS="null", XDG_CACHE_HOME=str(root / "cache"))
    for k in ["JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "GALLIUM_DRIVER", "LIBGL_KOPPER_DRI2", "VK_DRIVER_FILES"]:
        env.pop(k, None)
    java = [runtime["java"], "-Xms512m", "-Xmx2600m", "-XX:ActiveProcessorCount=4",
            "-Dorg.lwjgl.openal.libname=libopenal.so.1", "-cp", ":".join(runtime["cp"]),
            "net.fabricmc.loader.impl.launch.knot.KnotClient", "--username", "LanternVisitor", "--version", "1.21.1",
            "--gameDir", str(game), "--assetsDir", str(assets), "--assetIndex", "17",
            "--uuid", "00000000000040008000000000000432", "--accessToken", "0", "--userType", "legacy",
            "--width", str(W), "--height", str(H), "--quickPlaySingleplayer", WORLD]
    steps, notes = [], []
    p = None

    def text():
        return log.read_text(errors="replace")

    def x(*a, check=True, timeout=6):
        return subprocess.run(list(a), env=env, text=True, capture_output=True, check=check, timeout=timeout).stdout.strip()

    def window():
        r = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid", str(p.pid), "--name", "Minecraft"],
                           env=env, text=True, capture_output=True)
        return r.stdout.strip() if r.returncode == 0 and len(r.stdout.split()) == 1 else None

    def grab(wid, name):
        f = OUT / name
        x("ffmpeg", "-v", "error", "-n", "-f", "x11grab", "-window_id", wid, "-i", ":1", "-frames:v", "1", "-threads", "1", str(f))
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             env=env, capture_output=True, check=True).stdout
        n = len(raw) // 3
        mean = [round(sum(raw[c::3]) / n, 2) for c in range(3)]
        spread = max(raw[::97]) - min(raw[::97])
        steps.append(dict(file=name, bytes=len(raw), mean=mean, spread=spread, sha256=sha(f.read_bytes())))
        require(spread > 60, "frame looks uniform: " + name)
        return f

    def focused(wid):
        x("xdotool", "windowfocus", "--sync", wid)
        return x("xdotool", "getwindowfocus") == wid

    def hold(wid, key, seconds):
        require(focused(wid), "private window lost focus; no input sent")
        x("xdotool", "keydown", key)
        try:
            time.sleep(seconds)
        finally:
            x("xdotool", "keyup", key, check=False)

    with log.open("xb") as stream:
        p = subprocess.Popen(java, stdout=stream, stderr=stream, env=env, cwd=game)
        try:
            deadline = time.monotonic() + 300
            while "logged in with entity id" not in text():
                require(p.poll() is None and time.monotonic() < deadline, "never joined the world")
                time.sleep(0.5)
            joined = time.monotonic()
            t = text()
            renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t)
            require(renderer and lab.nvidia(renderer.group(1)), "not the NVIDIA renderer")
            require("Using shaderpack: " + PACK.name in t, "Iris did not select the pack")
            # Iris compiles the pack on the render thread (~105 s cold): the window is frozen until the
            # Aqualumen bridge logs its first initialisation, so wait for that line, then let chunks mesh.
            deadline = time.monotonic() + 420
            while not re.search(r"\[Aqualumen Physics\] .*bridge initialized", text()):
                require(p.poll() is None and time.monotonic() < deadline, "pipeline never finished")
                time.sleep(1)
            steps.append(dict(pipelineReadySecondsAfterJoin=round(time.monotonic() - joined, 1)))
            time.sleep(12)
            wid = window()
            require(wid, "private window not found")
            grab(wid, "01-spawn.png")
            time.sleep(1.5)
            grab(wid, "01-spawn-b.png")
            # --- a player's own inputs: walk down the path, right-click the front door, walk in
            hold(wid, "w", 3.4)
            time.sleep(0.8)
            grab(wid, "02-at-door.png")
            loc = x("xdotool", "getmouselocation", "--shell")
            under = dict(l.split("=") for l in loc.splitlines()).get("WINDOW")
            if under == wid:
                x("xdotool", "click", "3")
                notes.append("right click sent (pointer window == private window)")
            else:
                notes.append("right click NOT sent: pointer window %s != %s" % (under, wid))
            time.sleep(1.2)
            grab(wid, "03-door-open.png")
            hold(wid, "w", 2.0)
            time.sleep(1.5)
            grab(wid, "04-inside-room-a.png")
        finally:
            w = window() if p.poll() is None else None
            if w:
                subprocess.run(["/tmp/aqualumen-wm-close", hex(int(w))], check=False, env=env)
            try:
                p.wait(timeout=30)
            except subprocess.TimeoutExpired:
                p.terminate()
                p.wait(timeout=10)
    t = text()
    renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t).group(1).strip()
    errors = [l for l in t.splitlines() if re.search(r"/(ERROR|FATAL)\]|Exception|Failed to (load|read)|Couldn't", l)]
    (OUT / "log-errors.txt").write_text("\n".join(errors) + "\n")
    # the saved clone shows what the player did (door state) -- read with the independent validator decoder
    sys.path.insert(0, str(HERE))
    import validate_world as V

    chunks = V.read_chunks(saved / "region")
    blocks = V.decode_blocks(chunks)
    door = {str(k): blocks[k][1]["open"] for k in ((6, -60, 0), (6, -59, 0))}
    pdat = next((V.parse_nbt(gzip.decompress(f.read_bytes())) for f in (saved / "playerdata").glob("*.dat")), None)
    result = dict(
        savedPlayerPos=pdat["Pos"] if pdat else None, savedPlayerRotation=pdat["Rotation"] if pdat else None,
        when=time.strftime("%Y-%m-%dT%H:%M:%S%z"), lockAcquired=t_lock, renderer=renderer,
        glVersion=next((m.group(1).strip() for m in re.finditer(r"OpenGL Version: ([^\n]+)", t)), None),
        pack=PACK.name, packSha256=PACK_SHA, worldZip=WORLD_ZIP.name, worldZipSha256=world_zip_sha,
        gameDir=str(game), joinedLine=next(l for l in t.splitlines() if "logged in with entity id" in l),
        cleanShutdown="All dimensions are saved" in t, shaderFallback="Using shaderpack: " + PACK.name not in t,
        modsLoaded=sorted(mods), steps=steps, notes=notes, logErrors=errors[:20], logErrorCount=len(errors),
        frontDoorOpenInSavedClone=door, savedLevelHasPlayer=("Player" in V.parse_nbt(gzip.decompress((saved / "level.dat").read_bytes()))["Data"]),
        savedPlayerdataFiles=sorted(p.name for p in (saved / "playerdata").glob("*")) if (saved / "playerdata").exists() else [],
        labFilesUnchanged={n: sha((orig / n).read_bytes()) == h for n, h in guarded.items()},
        modsUnchanged={n: sha((orig / "mods" / n).read_bytes()) == h for n, h in mods.items()},
        deliveredZipUnchanged=sha(WORLD_ZIP.read_bytes()) == world_zip_sha,
    )
    require(all(result["labFilesUnchanged"].values()), "Lab config changed?!")
    (OUT / "smoke.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: result[k] for k in ("renderer", "cleanShutdown", "shaderFallback", "notes", "logErrorCount", "frontDoorOpenInSavedClone")}, indent=1))


if __name__ == "__main__":
    main()
