"""Ordinary survival play in a private clone of Aqualumen Woodland: walk, place/remove warm and soul torches behind a natural oak crown,
orbit the tree, walk to the water. Physical keyboard/mouse (xdotool) only; positions read from the vanilla F3 overlay.

  python3 -I run.py <run-name> <pack.zip> <world.zip> [--video] [--no-orbit] [--cave]

Safety: opt-in guard file (outside the save, in the throwaway game dir's parent) holding a per-run UUID, exact Java PID + cwd + the focused
window's PID are verified before every input. No commands, datapacks or benchmark mod; Lab instance only read-copied (mods/options/config).
"""
import argparse, fcntl, gzip, hashlib, importlib.util, json, math, os, re, shutil, string, subprocess, sys, tempfile, time, uuid
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from PIL import Image

evidence = Path(__file__).resolve().parent
here = evidence.parent / 'play'
root = here.parents[2]
sys.path.insert(0, str(root / "reports/2026-11-21-rain-eaves/journey"))
sys.path.insert(0, str(root / "tools"))
import hud            # noqa: E402  (vanilla F3 font decoder)
import route_fps      # noqa: E402  (integer "N fps" reader)
import ground_shadow_lab as g  # noqa: E402  (paths + option editing helpers only)

site = json.loads((evidence / "site-r1.json").read_text())
plan = json.loads((evidence / "final-route.json").read_text())

ap = argparse.ArgumentParser()
ap.add_argument("run"); ap.add_argument("pack", type=Path); ap.add_argument("world", type=Path)
ap.add_argument("--video", action="store_true"); ap.add_argument("--no-orbit", action="store_true"); ap.add_argument("--cave", action="store_true")
args = ap.parse_args()
W, H = 1600, 900
assert re.fullmatch(r"[a-z0-9-]+", args.run)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
write = lambda p, v: Path(p).write_text(json.dumps(v, indent=2, ensure_ascii=False) + "\n")
pack, world = args.pack.resolve(), args.world.resolve()
pack_sha, world_sha = sha(pack), sha(world)
out = evidence / args.run
out.mkdir()
orig = g.GAME.resolve()
guard_files = ["config/iris.properties", "options.txt", "config/sodium-options.json"]
original = {n: sha(orig / n) for n in guard_files}
mods = {n: sha(orig / "mods" / n) for n in g.lab.NORMAL_MODS}
write(out / "status.json", {"stage": "awaiting render lock", "pack": pack.name, "packSha256": pack_sha, "worldSha256": world_sha})
lock = open("/tmp/aql-render21-1000.lock", "a+b")
fcntl.flock(lock, fcntl.LOCK_EX)
t_lock = time.strftime("%H:%M:%S")
base = Path(tempfile.mkdtemp(prefix="aql-leaf-play-"))
game = base / "minecraft"
for d in ("saves", "mods", "config", "shaderpacks"):
    (game / d).mkdir(parents=True)
for n in mods:
    shutil.copyfile(orig / "mods" / n, game / "mods" / n)
assert {p.name for p in (game / "mods").iterdir()} == g.lab.NORMAL_MODS
shutil.copyfile(pack, game / "shaderpacks" / pack.name)
for n in ["config/iris.properties", "config/sodium-options.json"]:
    shutil.copyfile(orig / n, game / n)
iris = game / "config/iris.properties"
iris.write_bytes(g.lab.replace_values(iris.read_bytes(), {"shaderPack": pack.name}, "="))
opt = dict(g.lab.OPTIONS, fullscreen="false", maxFps="120", enableVsync="false", overrideWidth=str(W), overrideHeight=str(H), rawMouseInput="false",
           mouseSensitivity="0.5", guiScale="2", lang="en_us", forceUnicodeFont="false", pauseOnLostFocus="false", fov="0.0",
           fovEffectScale="0.0", bobView="false", reducedDebugInfo="false", autoJump="true")
(game / "options.txt").write_bytes(g.lab.replace_values((orig / "options.txt").read_bytes(), opt, ":"))
with ZipFile(world) as z:
    names = z.namelist()
    assert names == ["Aqualumen-Woodland/level.dat"]
    z.extractall(game / "saves")
save = game / "saves/Aqualumen-Woodland"
guard_id = str(uuid.uuid4())
guard = base / "input-opt-in.json"
identity = {"run": guard_id, "game": str(game.resolve()), "world": str(save.resolve()), "worldZipSha256": world_sha, "seed": site["seed"]}
write(guard, identity); write(out / "identity.json", identity)
runtime = json.loads((root / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
env = dict(os.environ, DISPLAY=":1", __GLX_VENDOR_LIBRARY_NAME="nvidia", ALSOFT_DRIVERS="null", XDG_CACHE_HOME=str(base / "cache"))
env["__GL_SHADER_DISK_CACHE_PATH"] = str(Path.home() / ".cache/aqualumen-lab-shader-driver")
for k in ["JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "GALLIUM_DRIVER", "LIBGL_KOPPER_DRI2", "VK_DRIVER_FILES"]:
    env.pop(k, None)
cmd = [runtime["java"], "-Xms512m", "-Xmx2600m", "-XX:ActiveProcessorCount=4", "-Dorg.lwjgl.openal.libname=libopenal.so.1", "-cp", ":".join(runtime["cp"]),
       "net.fabricmc.loader.impl.launch.knot.KnotClient", "--username", "Woodwalker", "--version", "1.21.1", "--gameDir", str(game),
       "--assetsDir", str(orig.parents[2] / "assets"), "--assetIndex", "17", "--uuid", "00000000000040008000000000000308", "--accessToken", "0",
       "--userType", "legacy", "--width", str(W), "--height", str(H), "--quickPlaySingleplayer", "Aqualumen-Woodland"]
logpath = out / "client.log"
obs, actions, fpsrec = [], [], []
st = {"start": None, "wid": None, "debug": False, "proc": None}


def x(*a, timeout=6):
    return subprocess.check_output(["xdotool", *a], env=env, timeout=timeout, text=True, stderr=subprocess.DEVNULL).strip()


def log():
    return logpath.read_text(errors="replace")


def guard_ok():
    p = st["proc"]
    assert json.loads(guard.read_text()) == identity and p.poll() is None
    assert Path("/proc", str(p.pid), "cwd").resolve() == game.resolve()
    assert x("getwindowpid", st["wid"]) == str(p.pid) and x("getwindowfocus") == st["wid"]


def key(k):
    guard_ok(); x("key", k)


def hold(k, seconds):
    guard_ok(); x("keydown", k)
    try:
        time.sleep(seconds)
    finally:
        x("keyup", k)
    time.sleep(.25)


def click(button):
    guard_ok(); x("click", button); time.sleep(.5)


def f3(active):
    if st["debug"] != active:
        key("F3"); time.sleep(.5 if active else .3); st["debug"] = active


def grab():
    d = subprocess.check_output(["ffmpeg", "-v", "error", "-f", "x11grab", "-window_id", st["wid"], "-i", env["DISPLAY"], "-frames:v", "1", "-threads", "1",
                                 "-pix_fmt", "bgr0", "-f", "rawvideo", "pipe:1"], env=env, timeout=8)
    assert len(d) == W * H * 4
    return Image.frombytes("RGB", (W, H), d, "raw", "BGRX")


def observe(label, keep=False):
    f3(True)
    for _ in range(6):
        im = grab(); rgb = np.asarray(im)
        pos = hud.position(rgb)
        ang = hud.row_text(rgb, "Facing: ", string.ascii_letters + "0123456789-.()/ ")
        m = re.search(r"\((-?[0-9.]+) / (-?[0-9.]+)\)", ang or "")
        if pos and m:
            break
        time.sleep(.3)
    else:
        im.save(out / "unreadable-hud.png"); raise RuntimeError("cannot read F3")
    rec = {"label": label, "t": round(time.monotonic() - st["start"], 2), "xyz": pos, "angle": list(map(float, m.groups())),
           "target": hud.target_block(rgb), "fps": route_fps.fps(rgb[:80, :320])}
    if keep:
        f = f"f3-{len(obs):03d}-{label}.png"; im.save(out / f); rec["f3Image"] = f
    obs.append(rec); write(out / "positions.json", obs)
    if rec["fps"] is not None:
        fpsrec.append({"label": label, "fps": rec["fps"], "t": rec["t"]})
    f3(False)
    return rec


def turn(yaw, pitch, rec):
    dyaw = (yaw - rec["angle"][0] + 180) % 360 - 180
    dx = round(max(-470, min(470, dyaw / .15))); dy = round(max(-250, min(250, (pitch - rec["angle"][1]) / .15)))
    guard_ok(); x("mousemove_relative", "--", str(dx), str(dy)); time.sleep(.3)


def aim(point, label, want=None, tries=4):
    """Aim the crosshair at world point; return the observation (target read from F3)."""
    for _ in range(tries):
        o = observe(label)
        px, py, pz = o["xyz"]
        dx, dz = point[0] - px, point[2] - pz
        yaw = math.degrees(math.atan2(-dx, dz)); pitch = math.degrees(math.atan2(py + 1.62 - point[1], math.hypot(dx, dz)))
        d = ((yaw - o["angle"][0] + 180) % 360 - 180, pitch - o["angle"][1])
        if abs(d[0]) < .3 and abs(d[1]) < .3 and (want is None or o["target"] == want):
            return o
        turn(yaw, pitch, o)
    return observe(label + "-final")


def goto(wp, label, tol=.5):
    tx, ty, tz = wp
    for _ in range(26):
        o = observe(label)
        px, py, pz = o["xyz"]
        dx, dz = tx - px, tz - pz; d = math.hypot(dx, dz)
        if d < tol:
            return o
        heading = math.degrees(math.atan2(-dx, dz))
        error = (heading-o["angle"][0]+180)%360-180
        turn(heading, 0.0, o)
        if abs(error)>65:
            # One mouse event is capped at 70.5 degrees. Finish the turn
            # before walking, including after a small waypoint overshoot.
            continue
        if wp[1] > o["xyz"][1] + .35 and ("cave" in label or "home" in label):
            # The sloped path includes real one-block rises. Use the normal jump
            # key explicitly; the player's auto-jump can stop at a diagonal corner.
            guard_ok();x("keydown","space")
            try:hold("w",min(2.4,d)/4.317*.72)
            finally:x("keyup","space")
        else:
            hold("w",min(5.0,d)/4.317*.70)
    raise RuntimeError(f"route stalled before {label}: {obs[-1]}")


def walk_leg(name, label, reverse=False):
    wps = plan["legs"][name]["waypoints"]
    wps = wps[::-1] if reverse else wps
    for i, wp in enumerate(wps[1:], 1):
        goto(wp, f"{label}-{i}")


def shot(name, still=1.0):
    f3(False); time.sleep(still)
    grab().save(out / f"{name}.png")
    return f"{name}.png"


def look_at(point, label):
    o = aim(point, label)
    return o


def inspect_cell(label):
    return observe(label, keep=True)


with logpath.open("xb") as stream:
    proc = subprocess.Popen(cmd, cwd=game, env=env, stdout=stream, stderr=stream)
    st["proc"] = proc
    video = vlog = None
    try:
        dl = time.monotonic() + 900
        while "logged in with entity id" not in log():
            assert proc.poll() is None and time.monotonic() < dl, "never joined"
            time.sleep(.5)
        t_join = time.monotonic()
        assert "OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" in log() and "Using shaderpack: " + pack.name in log()
        dl = time.monotonic() + 900
        while "contact bridge initialized" not in log():
            assert proc.poll() is None and time.monotonic() < dl and "disabling shaders" not in log().lower(), "pipeline"
            time.sleep(.6)
        pipeline_s = round(time.monotonic() - t_join, 1)
        time.sleep(6)
        ids = x("search", "--all", "--onlyvisible", "--pid", str(proc.pid), "--name", "Minecraft").split()
        assert len(ids) == 1
        st["wid"] = ids[0]; x("windowfocus", "--sync", st["wid"]); guard_ok()
        st["start"] = time.monotonic()
        if args.video:
            vlog = (out / "video.log").open("xb")
            video = subprocess.Popen(["ffmpeg", "-v", "error", "-n", "-f", "x11grab", "-framerate", "24", "-window_id", st["wid"], "-i", env["DISPLAY"],
                                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-threads", "3", "-pix_fmt", "yuv420p", str(out / "journey.mkv")],
                                     stdin=subprocess.PIPE, stdout=vlog, stderr=vlog, env=env)
        first = observe("spawn", keep=True)
        shot("spawn-first-camera")
        flame_warm = (site["warm_torch_cell"][0] + .5, site["warm_torch_cell"][1] + .7, site["warm_torch_cell"][2] + .5)
        top_face = (site["warm_torch_cell"][0] + .5, site["warm_torch_cell"][1] - .1, site["warm_torch_cell"][2] + .5)  # just inside the grass top
        ground_cell = (site["warm_torch_cell"][0], site["warm_torch_cell"][1] - 1, site["warm_torch_cell"][2])
        torch_cell = tuple(site["warm_torch_cell"])

        def view_flame(label):
            """From the viewing spot, look through the crown at the torch cell and capture."""
            o = look_at(flame_warm, label)
            names = [shot(f"{label}-{i}", 1.5) for i in range(3)]
            return {"obs": o, "images": names}

        results = {}
        walk_leg("spawn->place-north", "to-north")
        key("2")  # slot 1: torches
        o = aim(top_face, "aim-top-face", want=ground_cell)
        assert o["target"] == ground_cell, o
        click("3")
        o = aim((torch_cell[0] + .5, torch_cell[1] + .35, torch_cell[2] + .5), "torch-placed", want=torch_cell)
        actions.append({"action": "place torch", "cell": torch_cell, "targetReadback": o["target"], "xyz": o["xyz"], "t": o["t"]})
        write(out / "actions.json", actions)
        walk_leg("place-north->view", "to-view")
        results["warm"] = view_flame("warm")
        # warm/cold choice: bare hand removes the torch, the soul torch goes into the same cell
        walk_leg("place-north->view", "back-north", reverse=True)
        key("1")  # empty hand
        o = aim((torch_cell[0] + .5, torch_cell[1] + .35, torch_cell[2] + .5), "aim-torch", want=torch_cell)
        assert o["target"] == torch_cell, o
        click("1")
        o = aim((torch_cell[0] + .5, torch_cell[1] + .35, torch_cell[2] + .5), "torch-removed")
        actions.append({"action": "remove torch (bare hand)", "cell": torch_cell, "targetReadbackAfter": o["target"], "t": o["t"]})
        key("3")  # soul torches
        o = aim(top_face, "aim-top-face-soul", want=ground_cell)
        assert o["target"] == ground_cell, o
        click("3")
        o = aim((torch_cell[0] + .5, torch_cell[1] + .35, torch_cell[2] + .5), "soul-placed", want=torch_cell)
        actions.append({"action": "place soul torch", "cell": torch_cell, "targetReadback": o["target"], "t": o["t"]})
        write(out / "actions.json", actions)
        walk_leg("place-north->view", "to-view-2")
        results["soul"] = view_flame("soul")
        if not args.no_orbit:
            tree = (site["tree"]["base"][0] + .5, site["tree"]["base"][1] + 1.6, site["tree"]["base"][2] + .5)
            for k in range(4, 4 + 12):
                a, b = f"ring{k % 12}", f"ring{(k + 1) % 12}"
                for i, wp in enumerate(plan["legs"][f"{a}->{b}"]["waypoints"][1:], 1):
                    goto(wp, f"orbit-{a}-{i}")
                if (k - 4) % 3 == 2:
                    look_at(tree, f"orbit-look-{b}")
                    results.setdefault("orbit", []).append(shot(f"orbit-{(k - 4) // 3}", .8))
        walk_leg("view->water", "to-water")
        look_at((556.5, 62.0, 418.5), "water-look")
        results["water"] = shot("water-edge", 1.0)
        if args.cave:
            walk_leg("water->cave", "to-cave")
            results["cave"] = shot("cave-cell", 1.0)
            results["caveObs"] = observe("cave-arrive", keep=True)
            cave = plan["legs"]["water->cave"]["waypoints"][-1]
            assert math.dist(results["caveObs"]["xyz"], cave) < 0.85, results["caveObs"]
            walk_leg("cave->spawn", "home")
        end = observe("end", keep=True)
        if args.cave:
            home = plan["legs"]["cave->spawn"]["waypoints"][-1]
            assert math.dist(end["xyz"], home) < 0.85, end
        length = time.monotonic() - st["start"]
    finally:
        if video and video.poll() is None:
            video.stdin.write(b"q\n"); video.stdin.flush(); video.wait(timeout=30)
        if vlog:
            vlog.close()
        if st["wid"] and proc.poll() is None:
            subprocess.run(["/tmp/aqualumen-wm-close", hex(int(st["wid"]))], env=env, timeout=8)
        try:
            proc.wait(timeout=40)
        except subprocess.TimeoutExpired:
            proc.terminate(); proc.wait(timeout=12)
        guard.unlink(missing_ok=True)

sys.path.insert(0, str(root / "reports/2026-11-21-door-light/playable"))
from validate_world import parse_nbt  # noqa: E402
level = parse_nbt(gzip.decompress((save / "level.dat").read_bytes()))["Data"]
pfiles = sorted((save / "playerdata").glob("*.dat"))
player = parse_nbt(gzip.decompress(pfiles[0].read_bytes())) if pfiles else None
stats_files = list((save / "stats").glob("*.json"))
stats = json.loads(stats_files[0].read_text())["stats"] if stats_files else {}
t = log()
fpsvals = [r["fps"] for r in fpsrec]
record = {
    "run": args.run, "renderer": re.search(r"OpenGL Renderer: ([^\n]+)", t).group(1).strip(), "pack": pack.name, "packSha256": pack_sha,
    "worldZip": world.name, "worldZipSha256": world_sha, "lockAcquired": t_lock, "pipelineSecondsAfterJoin": pipeline_s,
    "seconds": round(length, 1), "video": bool(args.video), "recording": "x11grab 1600x900 24 fps libx264 crf20" if args.video else None,
    "cleanExit": "All dimensions are saved" in t, "logErrors": [l for l in t.splitlines() if re.search(r"/(ERROR|FATAL)\]|Exception", l)][:20],
    "results": results, "actions": actions, "firstObservation": first, "endObservation": end,
    "displayedFps": {"samples": len(fpsvals), "min": min(fpsvals) if fpsvals else None, "median": float(np.median(fpsvals)) if fpsvals else None,
                     "max": max(fpsvals) if fpsvals else None, "note": "Minecraft F3 integer FPS read from screenshots, F3 open, 1600x900 window, 12 chunks"},
    "savedLevel": {k: level[k] for k in ("Time", "DayTime", "raining", "rainTime", "clearWeatherTime", "GameType", "allowCommands", "Difficulty")},
    "savedPlayer": {"Pos": player["Pos"], "Rotation": player["Rotation"], "playerGameType": player.get("playerGameType")} if player else level.get("Player"),
    "walkMetres": stats.get("minecraft:custom", {}).get("minecraft:walk_one_cm", 0) / 100,
    "inputs": "xdotool keyboard+mouse to the exact PID window; guard file outside the save; no commands, datapacks, benchmark mod",
    "labFilesUnchanged": all(sha(orig / n) == v for n, v in original.items()), "modsUnchanged": all(sha(orig / "mods" / n) == v for n, v in mods.items()),
    "worldZipUnchanged": sha(world) == world_sha, "benchmarkSentinelPresent": g.SENTINEL.exists(), "privateGameDir": str(game),
}
assert record["labFilesUnchanged"] and record["modsUnchanged"] and not record["benchmarkSentinelPresent"]
write(out / "complete.json", record)
write(out / "status.json", {"stage": "complete", "seconds": round(length, 1)})
print(json.dumps({k: record[k] for k in ("cleanExit", "displayedFps", "savedLevel", "walkMetres", "pipelineSecondsAfterJoin")}, indent=1))
