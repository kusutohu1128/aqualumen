"""Ordinary private survival continuation from the saved shaded oak."""
import argparse, fcntl, gzip, hashlib, json, math, os, re, shutil, string, subprocess, sys, tempfile, time, uuid
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "reports/2026-11-21-leaf-light/play"
sys.path.insert(0, str(ROOT / "reports/2026-11-21-rain-eaves/journey"))
sys.path.insert(0, str(ROOT / "tools"))
import hud            # noqa: E402
import route_fps      # noqa: E402
import ground_shadow_lab as g  # noqa: E402

STABLE_SHA = "c5d804e4a6776cf7df14b405f32a605d09451cab10aabb8b3fae4c5428c73af8"
AUTHORISED = {"34c151e670501acb3a1bd3de8cf4bcc4b809652882b3a0b4ce05a6f5c260f088": "Aqualumen-1.9.0-preview.6.zip"}
COMPILER = ROOT / "dist/aqualumen-lighting-compiler-0.3.0.jar"
COMPILER_SHA = "c51cda673efd3526645f9d532d4422f0b713772f85c95786795ab812d8ee5142"
OWN = ROOT / "build/animal-light/woodland"
run_root = Path(__file__).resolve().parent
site = json.loads((SRC / "site.json").read_text())


ap = argparse.ArgumentParser()
ap.add_argument("--trail",default="trail.json"); ap.add_argument("run"); ap.add_argument("pack", type=Path); ap.add_argument("world", type=Path)
ap.add_argument("--video", action="store_true"); ap.add_argument("--revisit-from")
ap.add_argument("--preflight", action="store_true"); ap.add_argument("--cache-source", type=Path)
ap.add_argument("--village", action="store_true", help="Continue the saved snowy village journey instead of the oak trail")
ap.add_argument("--play-checkpoint",action="store_true",help="Use the verified portable world ZIP as the actual starting save")
ap.add_argument("--move-window", action="store_true", help="Rebuild the windows of the saved spruce house in survival")
ap.add_argument("--visit-window", action="store_true", help="Inspect the remodeled house from the village path")
ap.add_argument("--exposure-walk", action="store_true", help="Walk between the village house and the exposed road")
ap.add_argument("--exposure-readout", action="store_true", help="Record the diagnostic strip in the private village copy")
ap.add_argument("--forest-cave", action="store_true", help="Descend the natural rock staircase on seed 20261123")
args = ap.parse_args()
if not args.revisit_from and not args.forest_cave:
    ap.error("A previous save is required for this route")
if args.forest_cave and (args.village or args.play_checkpoint or args.exposure_walk):
    ap.error("The forest cave uses its own starter or saved cave run")
if args.exposure_walk and not args.village:
    ap.error("The road walk uses the saved village house")
if args.exposure_readout and not (args.village or args.forest_cave):
    ap.error("The exposure readout requires a village or forest cave route")
if (args.move_window or args.visit_window) and (not args.village or args.play_checkpoint or (args.move_window and args.visit_window)):
    ap.error("Choose one village window action and a previous house save")
world_folder = "Aqualumen-Woodland"
village_source=ROOT/"reports/2026-11-21-settlement-light/playable"
if args.village:
    site=json.loads((village_source/"starter.json").read_text())
    world_folder=site["worldFolder"]
    run_root=ROOT/"reports/2026-11-22-ceiling-return/village"
    run_root.mkdir(exist_ok=True)
if args.forest_cave:
    run_root=ROOT/"reports/2026-11-22-forest-cave"
    site=json.loads((run_root/"starter.json").read_text())
    world_folder=site["worldFolder"]
if args.village or args.forest_cave:
    AUTHORISED["c6f3c4a6a002cc1c0635c1b14a5ed3f92bed0d8937613ef1a01d448685bc967c"]="Aqualumen-1.9.0-preview.7.zip"
W, H = 1600, 900
assert re.fullmatch(r"[a-z0-9-]+", args.run)
assert not args.revisit_from or re.fullmatch(r"[a-z0-9-]+", args.revisit_from)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
write = lambda p, v: Path(p).write_text(json.dumps(v, indent=2, ensure_ascii=False) + "\n")


def progress(msg):
    with (run_root / "progress.txt").open("a") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")


pack, world = args.pack.resolve(), args.world.resolve()
pack_sha, world_sha = sha(pack), sha(world)
eye_report = ROOT/"reports/2026-11-22-eye-adaptation"
if args.exposure_readout or ((args.exposure_walk or args.forest_cave) and pack.name=="Aqualumen-1.9.0-preview.8.zip"):
    sys.path.insert(0,str(eye_report))
    from meter import candidate, candidate_bytes, instrument, release, release_sha
    assert sha(release)==release_sha
    if pack.name in ("Aqualumen-Window-Meter-8.zip",candidate.name):
        assert candidate.read_bytes()==candidate_bytes()
    if args.exposure_readout:
        model={"Aqualumen-Window-Meter-7.zip":release,"Aqualumen-Window-Meter-8.zip":candidate}[pack.name]
        assert pack.parent==candidate.parent and pack.read_bytes()==instrument(model)
    else:
        assert pack==candidate
else:
    assert AUTHORISED.get(pack_sha) == pack.name, f"{pack.name} {pack_sha} not authorised"
assert sha(COMPILER) == COMPILER_SHA
orig = g.GAME.resolve()
original = {n: sha(orig / n) for n in ["config/iris.properties", "options.txt", "config/sodium-options.json"]}
mods = {n: sha(orig / "mods" / n) for n in g.lab.NORMAL_MODS}


def save_digest(d):
    return {str(p.relative_to(d)): sha(p) for p in sorted(d.rglob("*")) if p.is_file() and p.name != "session.lock"}


if args.revisit_from:
    previous_dir = (ROOT/"reports/2026-11-21-ground-return/walk" if args.revisit_from=="ridge-revisit" else run_root) / args.revisit_from
    if args.village and args.revisit_from=="village-to-plains": previous_dir=village_source/args.revisit_from
    previous = json.loads((previous_dir / "complete.json").read_text())
    previous_id = json.loads((previous_dir / "identity.json").read_text())
    assert previous["cleanExit"] and not previous["logErrors"] and not previous["benchmarkSentinelPresent"]
    assert previous["worldZipSha256"] == world_sha
    prior_version=STABLE_SHA if args.village else "2fc286a1e07045eb0f7fc99a959a532161d521745d5939b29cb6acd4b48bcda3"
    previous_packs={pack_sha,prior_version}
    if args.village and (args.exposure_walk or args.exposure_readout):
        previous_packs.add("c6f3c4a6a002cc1c0635c1b14a5ed3f92bed0d8937613ef1a01d448685bc967c")
    assert previous["packSha256"] in previous_packs
    if args.village or args.forest_cave: assert world_sha==site["sha256"]
    assert previous["savedPlayer"]["playerGameType"] == previous["savedLevel"]["allowCommands"] == 0
    assert previous_id["seed"] == site["seed"]
    saved_source = Path(previous_id["world"]).resolve()
    allowed_folders = ({world_folder, "Aqualumen-Homecoming", "Aqualumen-Window-House"}
                       if args.village else {world_folder, "Aqualumen-Woodland-Expedition"})
    assert saved_source.name in allowed_folders and saved_source.parent==Path(previous["privateGameDir"]).resolve()/"saves"
    world_folder=saved_source.name
    assert saved_source.is_relative_to("/tmp") and not any(f.is_symlink() for f in saved_source.rglob("*"))
    if args.play_checkpoint:
        from zipfile import ZipFile
        checkpoint=json.loads((previous_dir/"save.json").read_text())
        archive=ROOT/checkpoint["archive"]
        assert archive.parent==ROOT/"dist" and sha(archive)==checkpoint["sha256"] and checkpoint["seed"]==site["seed"]
        restored=tempfile.TemporaryDirectory(prefix="aql-unpack-survival-")
        saved_source=Path(restored.name)
        world_folder=checkpoint["folder"]
        with ZipFile(archive) as z:
            assert {world_folder+"/"+n for n in checkpoint["members"]}==set(z.namelist())
            for n,digest in checkpoint["members"].items():
                dest=(saved_source/n).resolve()
                assert dest.is_relative_to(saved_source)
                data=z.read(world_folder+"/"+n)
                assert hashlib.sha256(data).hexdigest()==digest
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(data)
    source_player=previous["savedPlayer"]
    source_time=previous["savedLevel"]["Time"]
    source_metres=previous["walkMetres"]
else:
    from zipfile import ZipFile
    sys.path.insert(0,str(ROOT/"reports/2026-11-21-settlement-light/tools"))
    from mcnbt import load_gz
    assert args.forest_cave and world_sha==site["sha256"]
    restored=tempfile.TemporaryDirectory(prefix="aql-forest-starter-")
    saved_source=Path(restored.name)
    with ZipFile(world) as archive:
        assert archive.namelist()==[world_folder+"/level.dat"]
        (saved_source/"level.dat").write_bytes(archive.read(archive.namelist()[0]))
    data=load_gz(saved_source/"level.dat")["Data"]
    assert data["WorldGenSettings"]["seed"]==site["seed"] and data["GameType"]==data["allowCommands"]==0
    source_player={k:data["Player"][k] for k in ("Pos","Rotation","playerGameType")}
    source_time=data["Time"]
    source_metres=0
saved_before = save_digest(saved_source)
out = run_root / args.run
out.mkdir()
if args.preflight:
    write(out / "preflight.json", {"pack": pack.name, "packSha256": pack_sha, "world": world_sha, "files": len(saved_before),
                                   "sourceTime": source_time})
    progress(f"preflight {args.run} ok"); print("preflight ok"); sys.exit(0)
write(out / "status.json", {"stage": "awaiting render lock"})
progress(f"{args.run}: waiting for exclusive render lock")
lock = open("/tmp/aql-render21-1000.lock", "a+b")
fcntl.flock(lock, fcntl.LOCK_EX)
t_lock = time.strftime("%H:%M:%S")
write(out / "status.json", {"stage": "running", "lockAcquired": t_lock})
progress(f"{args.run}: lock acquired {t_lock}")
base = Path(tempfile.mkdtemp(prefix="aql-canopy-woodland-"))
game = base / "minecraft"
for d in ("saves", "mods", "config", "shaderpacks"):
    (game / d).mkdir(parents=True)
for n in mods:
    shutil.copyfile(orig / "mods" / n, game / "mods" / n)
shutil.copyfile(COMPILER, game / "mods" / COMPILER.name)
assert {p.name for p in (game / "mods").iterdir()} == g.lab.NORMAL_MODS | {COMPILER.name}
shutil.copyfile(pack, game / "shaderpacks" / pack.name)
for n in ["config/iris.properties", "config/sodium-options.json"]:
    shutil.copyfile(orig / n, game / n)
iris = game / "config/iris.properties"
iris.write_bytes(g.lab.replace_values(iris.read_bytes(), {"shaderPack": pack.name}, "="))
opt = dict(g.lab.OPTIONS, fullscreen="false", maxFps="60", enableVsync="false", overrideWidth=str(W), overrideHeight=str(H), rawMouseInput="false",
           mouseSensitivity="0.5", guiScale="2", lang="en_us", forceUnicodeFont="false", pauseOnLostFocus="false", fov="0.0",
           fovEffectScale="0.0", bobView="false", reducedDebugInfo="false", autoJump="true")
(game / "options.txt").write_bytes(g.lab.replace_values((orig / "options.txt").read_bytes(), opt, ":"))
save = game / "saves" / world_folder
shutil.copytree(saved_source, save, ignore=shutil.ignore_patterns("session.lock"))
assert save_digest(save) == saved_before
revisit = {"sourceRun": args.revisit_from, "copiedFiles": len(saved_before), "sourceSavedPlayer": source_player,
           "sourceSavedTime": source_time, "sourceWalkMetres": source_metres}
cache = OWN / "driver-cache" / pack_sha[:16]
if args.cache_source and not cache.exists():
    cache.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(args.cache_source, cache)
    progress(f"driver cache copied from {args.cache_source} ({sum(f.stat().st_size for f in cache.rglob('*') if f.is_file())} bytes)")
cache.mkdir(parents=True, exist_ok=True)
guard_id = str(uuid.uuid4())
guard = base / "input-opt-in.json"
identity = {"run": guard_id, "game": str(game.resolve()), "world": str(save.resolve()), "worldZipSha256": world_sha, "seed": site["seed"]}
write(guard, identity); write(out / "identity.json", identity)
runtime = json.loads((ROOT / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
DISPLAY_MIN = 240
vgl = Path((ROOT / "reports/2026-11-21-lava-light/runtime-v190/vgl-dir.txt").read_text().strip()) / "x/usr/lib"
assert (vgl / "libvglfaker.so").is_file() and (vgl / "libdlfaker.so").is_file()


def start_xvfb():
    for n in range(DISPLAY_MIN, DISPLAY_MIN + 40):
        if Path("/tmp/.X11-unix/X%d" % n).exists() or Path("/tmp/.X%d-lock" % n).exists():
            continue
        xl = (base / "xvfb.log").open("wb")
        pr = subprocess.Popen(["Xvfb", ":%d" % n, "-screen", "0", "%dx%dx24" % (W, H), "+extension", "GLX", "+extension", "RENDER", "-nolisten", "tcp", "-noreset"],
                              stdout=xl, stderr=xl, start_new_session=True)
        for _ in range(100):
            if Path("/tmp/.X11-unix/X%d" % n).exists() or pr.poll() is not None:
                break
            time.sleep(.1)
        if pr.poll() is None and Path("/tmp/.X11-unix/X%d" % n).exists():
            return pr, ":%d" % n
    raise RuntimeError("no free private display")


xvfb, display = start_xvfb()
assert int(display[1:]) >= DISPLAY_MIN and display != os.environ.get("DISPLAY")
env = {k: v for k, v in os.environ.items() if k not in ("WAYLAND_DISPLAY", "XAUTHORITY", "DISPLAY", "XDG_SESSION_TYPE", "LD_PRELOAD", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS")}
env.update(DISPLAY=display, ALSOFT_DRIVERS="null", __GL_SHADER_DISK_CACHE_PATH=str(cache), XDG_CACHE_HOME=str(base / "cache"),
           LD_PRELOAD="%s:%s" % (vgl / "libdlfaker.so", vgl / "libvglfaker.so"), VGL_DISPLAY="egl0", VGL_LOGO="0", VGL_COMPRESS="0", VGL_SPOIL="0", VGL_VERBOSE="1")
progress(f"{args.run}: private Xvfb {display}")
cmd = [runtime["java"], "-Xms512m", "-Xmx2600m", "-XX:ActiveProcessorCount=4", "-Dorg.lwjgl.openal.libname=libopenal.so.1", "-cp", ":".join(runtime["cp"]),
       "net.fabricmc.loader.impl.launch.knot.KnotClient", "--username", "Woodwalker", "--version", "1.21.1", "--gameDir", str(game),
       "--assetsDir", str(orig.parents[2] / "assets"), "--assetIndex", "17", "--uuid", "00000000000040008000000000000308", "--accessToken", "0",
       "--userType", "legacy", "--width", str(W), "--height", str(H), "--quickPlaySingleplayer", world_folder]
logpath = out / "client.log"
obs, actions, fpsrec, stops = [], [], [], []
st = {"start": None, "wid": None, "debug": False, "proc": None, "hud": True}


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


def mine(seconds):
    guard_ok()
    x("mousedown", "1")
    try:
        time.sleep(seconds)
    finally:
        x("mouseup", "1")
    time.sleep(.4)


def f3(active):
    if st["debug"] != active:
        key("F3"); time.sleep(.5 if active else .3); st["debug"] = active


def grab():
    d = subprocess.check_output(["ffmpeg", "-v", "error", "-f", "x11grab", "-window_id", st["wid"], "-i", display, "-frames:v", "1", "-threads", "1",
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


def goto(wp, label, tol=.32):
    tx, ty, tz = wp
    for _ in range(26):
        o = observe(label)
        px, py, pz = o["xyz"]
        dx, dz = tx - px, tz - pz; d = math.hypot(dx, dz)
        if d < tol:
            return o
        heading = math.degrees(math.atan2(-dx, dz))
        error = (heading - o["angle"][0] + 180) % 360 - 180
        turn(heading, 0.0, o)
        if abs(error) > 65:
            continue
        climbing = ty > py + .35
        if climbing:
            guard_ok(); x("keydown", "space")
        try:
            hold("w", min(2.2 if climbing else 5.0, d) / 4.317 * .70)
        finally:
            if climbing: x("keyup", "space")
    raise RuntimeError(f"route stalled before {label}: {obs[-1]}")


def hide_hud(hidden):
    if st["hud"] == hidden:
        key("F1"); time.sleep(.4); st["hud"] = not hidden


def retain_f2(name, before):
    deadline = time.monotonic() + 7
    while time.monotonic() < deadline:
        new = set((game / "screenshots").glob("*.png")) - before
        if len(new) == 1:
            src = next(iter(new))
            if src.stat().st_size > 0 and src.read_bytes()[-8:-4] == b"IEND":
                shutil.copy2(src, out / f"{name}-ingame.png"); return f"{name}-ingame.png"
        time.sleep(.1)
    raise RuntimeError("no unique complete F2 screenshot for " + name)


def shot(name, still=1.0, f2=False):
    f3(False); hide_hud(True); time.sleep(still)
    grab().save(out / f"{name}.png")
    if f2:
        before = set((game / "screenshots").glob("*.png"))
        key("F2"); retain_f2(name, before)
    hide_hud(False)
    return f"{name}.png"


def attempt(fn, name, results):
    """Auxiliary action: on failure record the real world position and carry on."""
    try:
        fn()
        results.setdefault("completed", []).append(name)
    except Exception as e:  # noqa: BLE001
        results.setdefault("failed", []).append({"step": name, "error": repr(e)[:300], "lastObservation": obs[-1] if obs else None})
        progress(f"{args.run}: step {name} failed: {e!r:.200}")
        try:
            observe("after-failure-" + name, keep=True)
        except Exception:
            pass


def hotbar():
    sys.path.insert(0,str(ROOT/"reports/2026-11-21-settlement-light/tools"))
    from mcnbt import load_gz
    players=list((saved_source/"playerdata").glob("*.dat"))
    assert len(players)==1
    return {str(i["Slot"]+1):i["id"] for i in load_gz(players[0])["Inventory"] if 0<=i["Slot"]<9}


def photograph_lights(prefix,point,already_facing=False):
    if not already_facing: aim(point,prefix)
    inventory=hotbar()
    controls=[("1","empty",None),("2","torch","minecraft:torch"),("3","soul-torch","minecraft:soul_torch"),("1","empty-restored",None)]
    assert all(inventory.get(k)==item for k,_,item in controls)
    photos=[]
    hide_hud(True)
    try:
        for k,label,item in controls:
            key(k); time.sleep(.7)
            before=set((game/"screenshots").glob("*.png"))
            key("F2")
            photos.append({"file":retain_f2(prefix+"-"+label,before),"key":k,"held":item,"t":round(time.monotonic()-st["start"],2)})
    finally:
        hide_hud(False)
    return photos


def trace_herd():
    import trail
    results["inventoryKeys"]=hotbar()
    if args.revisit_from=="pasture":
        results["oakPhotos"]=photograph_lights("oak",(602.8,70.,367.5))
    series=[]
    for leg in range(16):
        player_obs=observe("animal-trail-"+str(leg))
        # A single-player pause flushes the integrated server's normal save.
        offset=len(log())
        key("Escape")
        try:
            deadline=time.monotonic()+6
            while "Saving and pausing game" not in log()[offset:] and time.monotonic()<deadline:
                time.sleep(.15)
            assert "Saving and pausing game" in log()[offset:], "single-player pause unconfirmed"
            time.sleep(.7)
            route=trail.build(args.revisit_from,save,player_obs["xyz"],True)
        finally:
            key("Escape");time.sleep(.35)
        write(out/("herd-route-%02d.json"%leg),route)
        points=route["waypoints"]
        target=route["targetCow"]
        pos=target["position"]
        feet=player_obs["xyz"]
        dx,dz=pos[0]-feet[0],pos[2]-feet[2]
        distance=math.hypot(dx,dz)
        if distance<12. and trail.visible(tuple(map(math.floor,feet)),pos):
            yaw=math.degrees(math.atan2(-dx,dz))
            pitch=math.degrees(math.atan2(feet[1]+1.62-pos[1]-.9,distance))
            click("2")
            point=(pos[0],pos[1]+.9,pos[2])
            frame=aim(point,"face-grazing-"+str(leg),tries=6)
            if abs((yaw-frame["angle"][0]+180)%360-180)>1 or abs(pitch-frame["angle"][1])>1:
                continue
            photos=photograph_lights("graze-%02d"%leg,pos,True)
            series.append(dict(cow=target,range=distance,feet=feet,actualPose=frame,photos=photos))
            results["grazingSeries"]=series
            write(out/"sightings.json",series)
            if len(series)>=4 or len(series)>=2 and distance<4.:return
        if len(points)==1: continue
        for i,wp in enumerate(points[1:4]):
            goto(wp,"herd-%02d-%d"%(leg,i),.4)
    raise RuntimeError("herd kept moving beyond sight during the walk")


with logpath.open("xb") as stream:
    proc = subprocess.Popen(cmd, cwd=game, env=env, stdout=stream, stderr=stream, start_new_session=True)
    st["proc"] = proc
    video = vlog = strip = None
    results = {}
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
        progress(f"{args.run}: joined, pipeline ready {pipeline_s}s")
        time.sleep(6)
        ids = x("search", "--all", "--onlyvisible", "--pid", str(proc.pid), "--name", "Minecraft").split()
        assert len(ids) == 1
        st["wid"] = ids[0]; x("windowfocus", "--sync", st["wid"]); guard_ok()
        x("mousemove", "--window", st["wid"], "800", "450"); time.sleep(.5)
        st["start"] = time.monotonic()
        if args.exposure_readout:
            from house import record_strip
            strip=record_strip(out,display,env)
            strip.__enter__()
        if args.video:
            vlog = (out / "video.log").open("xb")
            video = subprocess.Popen(["ffmpeg", "-v", "error", "-n", "-f", "x11grab", "-framerate", "24", "-window_id", st["wid"], "-i", display,
                                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-threads", "3", "-pix_fmt", "yuv420p", str(out / "journey.mkv")],
                                     stdin=subprocess.PIPE, stdout=vlog, stderr=vlog, env=env)
        first = observe("spawn", keep=True)
        assert math.dist(first["xyz"], revisit["sourceSavedPlayer"]["Pos"]) < .03, (first, revisit)
        shot("spawn-first-camera")
        key("1")
        # 1. prove that input really turns the camera before any long walk
        ok = False
        for attempt_no in range(4):
            o = observe(f"yaw-proof-{attempt_no}")
            turn(o["angle"][0] + 20, 0.0, o)
            o2 = observe(f"yaw-proof-{attempt_no}-after")
            moved = abs((o2["angle"][0] - o["angle"][0] + 180) % 360 - 180)
            results.setdefault("yawProof", []).append({"before": o["angle"], "after": o2["angle"], "deg": round(moved, 2)})
            if moved > 5:
                ok = True; break
            x("mousemove", "--window", st["wid"], "800", "450"); click("2")   # middle click captures the mouse without attacking in survival
        progress(f"{args.run}: yaw proof ok={ok} {results['yawProof'][-1]}")
        assert ok, "mouse look does not change yaw on the private display"
        if not (args.village or args.forest_cave):
            path=json.loads((run_root/args.trail).read_text())
            assert path["previous"]==args.revisit_from
        def outing():
            key("8")
            if args.revisit_from=="ridge-revisit":
                o=aim((561.5,63.35,422.5),"check-saved-fire",want=(561,63,422))
                assert o["target"]==(561,63,422)
                shot("saved-oak",f2=True)
            key("3")
            points=path["waypoints"]
            idx=min(range(len(points)),key=lambda i:math.dist(points[i],first["xyz"]))
            for i,point in enumerate(points[idx+1:],idx+1):
                position=goto(point,"trail-"+str(i),.42)
                if i in (8,26,38):
                    aim(points[min(i+3,len(points)-1)],"look-ahead")
                    shot("trail-"+str(i),f2=True)
            results["lastWaypoint"]=position if idx+1<len(points) else first
            sys.path.insert(0,str(ROOT/"reports/2026-11-21-settlement-light/tools"))
            from mcnbt import Region
            cows=[]
            for filename in (save/"entities").glob("*.mca"):
                r=Region(filename)
                for cx,cz in r.present():
                    for e in r.chunk(cx,cz).get("Entities",[]):
                        if e["id"]=="minecraft:cow":
                            cows.append(e["Pos"])
            point=min(cows,key=lambda pos: math.dist(pos,points[-1]))
            results["nearestSavedCow"]=point
            for slot,tag in [("1","empty-hand"),("3","soul-light"),("2","warm-light")]:
                key(slot)
                results[tag]=aim((point[0],point[1]+.9,point[2]),tag)
                shot(tag,1.2,f2=True)
            key("8")
            # Photograph neighbouring slopes too; grazing animals can leave the saved position.
            for angle in (-55,0,55):
                o=observe("pasture-pan")
                yaw=results["empty-hand"]["angle"][0]+angle
                turn(yaw,3,o)
                shot("pan-"+str(angle),f2=True)
        if args.village:
            sys.path.insert(0,str(run_root))
            from return_home import visit, relight, move_window, see_window
            if args.move_window:
                attempt(lambda: move_window(results,aim,shot,key,click,mine,hotbar),"move-house-window",results)
            elif args.visit_window:
                attempt(lambda: see_window(results,aim,goto,shot,key,click,mine,observe),"window-from-porch",results)
            elif args.play_checkpoint and not args.exposure_walk:
                results["archiveLoaded"]=checkpoint["sha256"]
                attempt(lambda: relight(results,aim,shot,key,click),"relight-at-home",results)
            elif not args.exposure_walk:
                attempt(lambda: visit(village_source,first,results,aim,goto,shot,key,click,observe,hotbar),"snow-village-homecoming",results)
            if args.exposure_walk:
                sys.path.insert(0,str(eye_report))
                from house import walk
                attempt(lambda: walk(village_source,first,results,aim,goto,shot,key,click,observe),"porch-to-road-and-back",results)
        elif args.forest_cave:
            sys.path.insert(0,str(run_root))
            from cave_walk import visit
            attempt(lambda: visit(results,aim,goto,shot,key,click,observe),"natural-cave",results)
        elif args.revisit_from in ("pasture","portrait","grazing"):
            attempt(trace_herd,"lit-oak-and-grazing-herd",results)
        else:
            attempt(outing,"saved-woodland-to-pasture",results)

        end = observe("end", keep=True)
        length = time.monotonic() - st["start"]
    finally:
        if strip:
            try:
                strip.__exit__(None,None,None)
            except (OSError,RuntimeError,subprocess.TimeoutExpired) as error:
                results["stripFailure"]=str(error)
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
        xvfb.terminate()

sys.path.insert(0, str(ROOT / "reports/2026-11-21-door-light/playable"))
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
    "compilerJarSha256": COMPILER_SHA, "mods": sorted(p.name for p in (game / "mods").iterdir()),
    "worldZipSha256": world_sha, "lockAcquired": t_lock, "pipelineSecondsAfterJoin": pipeline_s, "seconds": round(length, 1),
    "video": bool(args.video), "cleanExit": "All dimensions are saved" in t,
    "logErrors": [l for l in t.splitlines() if re.search(r"/(ERROR|FATAL)\]|Exception", l)][:20],
    "results": results, "actions": actions, "gridStops": stops, "firstObservation": first, "endObservation": end,
    "displayedFps": {"samples": len(fpsvals), "min": min(fpsvals) if fpsvals else None, "median": float(np.median(fpsvals)) if fpsvals else None,
                     "max": max(fpsvals) if fpsvals else None, "note": "displayed F3 integer FPS only, F3 open, 1600x900, 12 chunks; not a benchmark"},
    "savedLevel": {k: level[k] for k in ("Time", "DayTime", "raining", "GameType", "allowCommands", "Difficulty")},
    "savedPlayer": {"Pos": player["Pos"], "Rotation": player["Rotation"], "playerGameType": player.get("playerGameType")} if player else None,
    "walkMetres": stats.get("minecraft:custom", {}).get("minecraft:walk_one_cm", 0) / 100,
    "labFilesUnchanged": all(sha(orig / n) == v for n, v in original.items()), "modsUnchanged": all(sha(orig / "mods" / n) == v for n, v in mods.items()),
    "worldZipUnchanged": sha(world) == world_sha, "benchmarkSentinelPresent": g.SENTINEL.exists(), "privateGameDir": str(game),
    "previousSaveUnchanged": save_digest(saved_source) == saved_before, "revisit": revisit,
}
record["walkedAfterReloadMetres"] = round(record["walkMetres"] - revisit["sourceWalkMetres"], 2)
write(out / "complete.json", record)
write(out / "status.json", {"stage": "complete", "seconds": round(length, 1)})
progress(f"{args.run}: complete cleanExit={record['cleanExit']} walked={record['walkedAfterReloadMetres']}m time={record['savedLevel']['Time']}")
print(json.dumps({k: record[k] for k in ("cleanExit", "displayedFps", "savedLevel", "walkedAfterReloadMetres")}, indent=1))
