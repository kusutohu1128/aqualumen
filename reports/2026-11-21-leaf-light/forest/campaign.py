"""Native forest leaf-transport acceptance run in a private, exact-UUID/seed copy of the V2 world (ordinary client:
the three normal mods, no recorder). Geometry: site.json (choose.py). One client per run; all stages once.

    python3 -I campaign.py dry                                   # datapack + static checks only (no lock, no launch)
    python3 -I campaign.py run <pack.zip> <run-name>              # one native run -> forest/<run-name>/
    python3 -I campaign.py campaign                              # 1.7.0 base-r1, then waits for 1.8.0-leaf-rc1 -> rc1-r1
    python3 -I campaign.py compare <runA> <runB>                 # before/after sheets + patch table

Stage cycle (datapack, repeats until the client exits): BEGIN -> set blocks/time/weather/pose -> after CHECK ticks
count every natural cell (persistent=false leaves, logs), reserved cells, supports, pose/mode, entity-free site,
frozen time, clear weather -> READY (or FAIL); then re-verify every 10 ticks and say DRIFT on any change.
"""
import fcntl
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "reports/2026-11-21-indirect-light"))
import capture as base  # noqa: E402

SITE = json.loads((HERE / "site.json").read_text())
LOCK = "/tmp/aql-render21-1000.lock"
CAMPAIGN_LOCK = "/tmp/aql-leaf-forest-campaign.lock"
PLAYER = "AqlForest"
PLAYER_UUID = "00000000000040008000000000000461"
PLAYER_FILE = "00000000-0000-4000-8000-000000000461.dat"
NS = "aqlf"
PACK_NAME = "LeafForest"
WIDTH, HEIGHT = 1600, 900
PERIOD, CHECK = 240, 100   # ticks per still stage; verified READY after CHECK ticks
SETTLE, DWELL, PAIR = 8.0, 3.0, 0.6
CLIP_TICKS = 200
BASE_PACK = ROOT / "dist/Aqualumen-1.7.0.zip"
RC1 = ROOT / "build/Aqualumen-1.8.0-leaf-rc1.zip"
STATUS = HERE / "status.json"
LIVE_RE = re.compile(r"Creating pipeline for dimension minecraft:overworld.*?Started [1-9]\d* worker threads", re.S)
EVENT_RE = re.compile(r"\[Server\] AQF_(READY|FAIL|DRIFT|BEGIN|ABORT|LIGHT)_([a-z0-9-]+)_END")
NIGHT = SITE["torch"]["time"]
DAYT = SITE["day"]["time"]
T, D = SITE["torch"], SITE["day"]
AIR = "minecraft:air"
TORCH, SOUL, STONE = "minecraft:torch", "minecraft:soul_torch", "minecraft:stone"


def c3(c):
    return "%d %d %d" % tuple(c)


def f3(v):
    return " ".join(fmt(x) for x in v)


def fmt(x):
    s = ("%.4f" % x).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def wrap(a):
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def pose_of(name):
    return SITE["poses"][name]


def tp(p):
    return "tp %s %s %s %s" % (PLAYER, " ".join(fmt(v) for v in p["feet"]), fmt(p["yaw"]), fmt(p["pitch"]))


def selector(p):
    return "@a[name=%s,distance=..0.01,gamemode=spectator,x_rotation=%s..%s,y_rotation=%s..%s]" % (
        PLAYER, fmt(p["pitch"] - .05), fmt(p["pitch"] + .05), fmt(wrap(p["yaw"] - .05)), fmt(wrap(p["yaw"] + .05)))


# block states per variant (reserved cells only; natural cells are never written)
def blocks(variant):
    st = {tuple(c): AIR for c in SITE["reservedAir"]}
    s1, s2 = tuple(T["warmSlot"]), tuple(T["soulSlot"])
    if variant in ("warm", "blocked", "restored", "orbit-warm"):
        st[s1] = TORCH
    if variant == "soul":
        st[s1] = SOUL
    if variant == "both":
        st[s1] = TORCH
        st[s2] = SOUL
    if variant == "blocked":
        for c in T["blocker"]:
            st[tuple(c)] = STONE
    if variant == "day-wall":
        for c in D["wall"]:
            st[tuple(c)] = STONE
    return st


TIME = {"off": NIGHT, "warm": NIGHT, "soul": NIGHT, "both": NIGHT, "blocked": NIGHT, "restored": NIGHT, "orbit-warm": NIGHT,
        "day-open": DAYT, "day-wall": DAYT, "day-restored": DAYT, "night-dark": NIGHT, "orbit-day": DAYT}
STILLS = [(v, p) for v in ("off", "warm", "soul", "both", "blocked", "restored") for p in ("torch-close", "torch-wide")] + \
         [(v, p) for v in ("day-open", "day-wall", "day-restored", "night-dark") for p in ("day-close", "day-wide")]
CLIPS = [("orbit-warm", "torch"), ("orbit-day", "day")]


def item_name(v, p):
    return "%s--%s" % (v, p)


def orbit(kind, k):
    """Camera on a horizontal arc (+-35 deg) around the leaf front, always aimed at the leaf face centre."""
    leaf, n = (T["leaf"], T["faceNormal"]) if kind == "torch" else (D["leaf"], D["faceNormal"])
    fc = [leaf[i] + .5 + n[i] * .5 for i in range(3)]
    base_pose = pose_of(kind + "-close")
    r = math.hypot(base_pose["eye"][0] - fc[0], base_pose["eye"][2] - fc[2]) + 0.6
    a0 = math.atan2(n[2], n[0])
    a = a0 + math.radians(35) * math.sin(2 * math.pi * k / CLIP_TICKS)
    eye = (fc[0] + r * math.cos(a), base_pose["eye"][1], fc[2] + r * math.sin(a))
    d = [fc[i] - eye[i] for i in range(3)]
    ln = math.sqrt(sum(x * x for x in d))
    yaw = math.degrees(math.atan2(-d[0], d[2]))
    pitch = math.degrees(-math.asin(d[1] / ln))
    return dict(feet=[eye[0], eye[1] - 1.62, eye[2]], eye=list(eye), yaw=yaw, pitch=pitch)


def datapack():
    fn = {}
    items = [item_name(v, p) for v, p in STILLS] + [c for c, _ in CLIPS]
    natural = SITE["natural"]
    reserved = [tuple(c) for c in SITE["reservedAir"]]
    lo = [min(c[i] for c in reserved + [tuple(map(int, k.split())) for k in natural]) for i in range(3)]
    hi = [max(c[i] for c in reserved + [tuple(map(int, k.split())) for k in natural]) for i in range(3)]
    lo[0], lo[2], hi[0], hi[2] = lo[0] - 12, lo[2] - 12, hi[0] + 12, hi[2] + 12
    fn["tick"] = ["execute as @a[name=%s,tag=!aqlf_started] run function %s:start" % (PLAYER, NS)]
    fn["start"] = ["tag @s add aqlf_started"] + ["gamerule %s" % g for g in (
        "doDaylightCycle false", "doWeatherCycle false", "doMobSpawning false", "randomTickSpeed 0", "doFireTick false",
        "doTileDrops false", "sendCommandFeedback false", "commandBlockOutput false", "announceAdvancements false",
        "doEntityDrops false", "doPatrolSpawning false", "doTraderSpawning false")] + [
        "difficulty peaceful", "weather clear", "time set %d" % NIGHT, "gamemode spectator @s",
        "scoreboard objectives add %s dummy" % NS, "scoreboard players set #attempt %s 0" % NS,
        "forceload add %d %d %d %d" % (lo[0], lo[2], hi[0], hi[2]), tp(pose_of("torch-close")),
        "schedule function %s:setup 20t replace" % NS]
    corners = " ".join("if loaded %d %d %d" % (x, lo[1], z) for x in (lo[0], hi[0]) for z in (lo[2], hi[2]))
    fn["setup"] = ["scoreboard players add #attempt %s 1" % NS, "scoreboard players set #loaded %s 0" % NS,
                   "execute %s run scoreboard players set #loaded %s 1" % (corners, NS),
                   "execute if score #loaded %s matches 0 if score #attempt %s matches ..90 run schedule function %s:setup 20t replace" % (NS, NS, NS),
                   "execute if score #loaded %s matches 0 if score #attempt %s matches 91.. run say AQF_ABORT_unloaded_END" % (NS, NS),
                   "execute if score #loaded %s matches 1 run function %s:reserve" % (NS, NS)]
    # positive AIR count of every reserved cell before anything is written
    fn["reserve"] = ["scoreboard players set #n %s 0" % NS] + [
        "execute if block %s %s run scoreboard players add #n %s 1" % (c3(c), AIR, NS) for c in reserved] + [
        "function %s:vnatural" % NS,
        "execute if score #n %s matches %d run schedule function %s:s0 20t replace" % (NS, len(reserved) + len(natural) + 2, NS),
        "execute unless score #n %s matches %d run say AQF_ABORT_reserved_END" % (NS, len(reserved) + len(natural) + 2)]
    fn["vnatural"] = ["execute if block %s %s run scoreboard players add #n %s 1" % (k, v, NS) for k, v in sorted(natural.items())] + [
        "execute if block %s %s run scoreboard players add #n %s 1" % (k, v, NS) for k, v in sorted(T["supports"].items())]
    site_c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    no_entities = "positioned %s unless entity @e[type=!minecraft:player,distance=..20]" % f3(site_c)
    fn["clean"] = ["execute positioned %s run kill @e[type=!minecraft:player,distance=..24]" % f3(site_c)]
    total = len(reserved) + len(natural) + 2
    n_items = len(items)
    front = [T["leaf"][i] + T["faceNormal"][i] for i in range(3)]
    for i, name in enumerate(items):
        clip = i >= len(STILLS)
        if clip:
            variant, kind = name, dict(CLIPS)[name]
            pose = orbit(kind, 0)
        else:
            variant, pname = STILLS[i]
            pose = pose_of(pname)
        st = blocks(variant)
        scene = ["schedule clear %s:h%d" % (NS, j) for j in range(n_items)] + ["schedule clear %s:o%d" % (NS, k) for k in range(CLIP_TICKS)]
        scene += ["say AQF_BEGIN_%s_END" % name, "time set %d" % TIME[variant], "weather clear", "function %s:clean" % NS]
        # remove stone first, then place emitters (stone cells never share emitter cells)
        scene += ["setblock %s %s" % (c3(c), b) for c, b in sorted(st.items()) if b == AIR]
        scene += ["setblock %s %s" % (c3(c), b) for c, b in sorted(st.items()) if b != AIR]
        scene += [tp(pose), "schedule function %s:c%d %dt replace" % (NS, i, CHECK)]
        nxt = PERIOD if not clip else CHECK + CLIP_TICKS + 60
        scene += ["schedule function %s:s%d %dt replace" % (NS, (i + 1) % n_items, nxt)]
        fn["s%d" % i] = scene
        verify = ["scoreboard players set #n %s 0" % NS, "scoreboard players set #ok %s 0" % NS, "function %s:vnatural" % NS]
        verify += ["execute if block %s %s run scoreboard players add #n %s 1" % (c3(c), b, NS) for c, b in sorted(st.items())]
        verify += ["execute store result score #t %s run time query daytime" % NS]
        cond = "if score #n %s matches %d if score #t %s matches %d if predicate %s:clear %s" % (NS, total, NS, TIME[variant], NS, no_entities)
        if not clip:
            cond += " positioned %s if entity %s" % (" ".join(fmt(v) for v in pose["feet"]), selector(pose))
        verify += ["execute %s run scoreboard players set #ok %s 1" % (cond, NS)]
        fn["v%d" % i] = verify
        fn["c%d" % i] = ["function %s:v%d" % (NS, i),
                         "execute if score #ok %s matches 1 run say AQF_READY_%s_END" % (NS, name),
                         "execute if score #ok %s matches 0 run say AQF_FAIL_%s_END" % (NS, name)] + [
                         "execute positioned %s if predicate %s:light%d run say AQF_LIGHT_%s-l%d_END" % (c3(front), NS, k, name, k) for k in range(16)] + [
                         "schedule function %s:h%d 10t replace" % (NS, i)] + (["function %s:o0" % NS] if clip else [])
        fn["h%d" % i] = ["function %s:v%d" % (NS, i), "execute if score #ok %s matches 0 run say AQF_DRIFT_%s_END" % (NS, name),
                         "schedule function %s:h%d 10t replace" % (NS, i)]
    # orbit chains (one shared chain per clip kind is enough: the clip item index decides which)
    for k in range(CLIP_TICKS):
        lines = []
        for idx, (cname, kind) in enumerate(CLIPS):
            lines.append("execute if score #clip %s matches %d run %s" % (NS, idx, tp(orbit(kind, k))))
        if k + 1 < CLIP_TICKS:
            lines.append("schedule function %s:o%d 1t replace" % (NS, k + 1))
        fn["o%d" % k] = lines
    for idx, (cname, _) in enumerate(CLIPS):
        i = items.index(cname)
        fn["s%d" % i].insert(0, "scoreboard players set #clip %s %d" % (NS, idx))
    files = {"pack.mcmeta": json.dumps({"pack": {"pack_format": 48, "description": "Private Aqualumen forest leaf fixture"}}),
             "data/minecraft/tags/function/tick.json": json.dumps({"values": [NS + ":tick"]}),
             "data/%s/predicate/clear.json" % NS: json.dumps({"condition": "minecraft:weather_check", "raining": False, "thundering": False})}
    for k in range(16):
        files["data/%s/predicate/light%d.json" % (NS, k)] = json.dumps(
            {"condition": "minecraft:location_check", "predicate": {"light": {"light": {"min": k, "max": k}}}})
    for k, lines in fn.items():
        files["data/%s/function/%s.mcfunction" % (NS, k)] = "\n".join(lines) + "\n"
    return files, items, dict(lo=lo, hi=hi)


def check(files, items):
    fdir = "data/%s/function/" % NS
    allowed = {tuple(c) for c in SITE["reservedAir"]}
    natural = set(SITE["natural"])
    for path, text in files.items():
        for line in text.splitlines():
            m = re.match(r"^setblock (-?\d+) (-?\d+) (-?\d+) (\S+)$", line)
            if m:
                c = tuple(map(int, m.groups()[:3]))
                base.require(c in allowed and "%d %d %d" % c not in natural, "write outside reserved: " + line)
            base.require(not line.startswith("fill "), "fill used")
    for i, name in enumerate(items):
        base.require("AQF_READY_%s_END" % name in files[fdir + "c%d.mcfunction" % i], name)
    base.require(not set(map(tuple, SITE["reservedAir"])) & {tuple(map(int, k.split())) for k in natural}, "reserved overlaps natural")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def status(update):
    cur = json.loads(STATUS.read_text()) if STATUS.exists() else {}
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(cur.get(k), dict):
            cur[k].update(v)
        else:
            cur[k] = v
    cur["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(cur, indent=2))
    os.replace(tmp, STATUS)


def patch_stats(raw, rect):
    x0, y0, x1, y1 = rect
    acc = [0, 0, 0]
    for y in range(y0, y1):
        row = raw[(y * WIDTH + x0) * 3:(y * WIDTH + x1) * 3]
        for c in range(3):
            acc[c] += sum(row[c::3])
    n = (x1 - x0) * (y1 - y0)
    return [round(a / n, 3) for a in acc]


def run(pack, name):
    base.require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", name) is not None, "run name")
    out = HERE / name
    base.require(not out.exists(), "run dir exists")
    pack = Path(pack)
    base.require(pack.is_file() and not pack.is_symlink() and pack.suffix == ".zip", "pack")
    pack = pack.resolve()
    pack_sha = sha(pack)
    files, items, box = datapack()
    check(files, items)
    sys.path.insert(0, str(ROOT / "tools"))
    import ground_shadow_lab as g
    lab = g.lab
    status({"runs": {name: dict(state="waiting-render-lock", pack=str(pack), sha256=pack_sha, queued=time.strftime("%H:%M:%S"))}})
    lock = open(LOCK, "a+b")
    fcntl.flock(lock, fcntl.LOCK_EX)
    t_start = time.time()
    status({"runs": {name: dict(state="cloning", started=time.strftime("%H:%M:%S"))}})
    orig = g.GAME.resolve()
    runtime = json.loads((ROOT / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
    src = orig / "saves" / lab.WORLD
    originals = {n: sha(orig / n) for n in ("options.txt", "config/iris.properties", "config/sodium-options.json") if (orig / n).is_file()}
    mods = {n: sha(orig / "mods" / n) for n in sorted(lab.NORMAL_MODS)}
    out.mkdir()
    parent = Path(tempfile.mkdtemp(prefix="aql-leaf-forest-%s-" % name))
    game = parent / "minecraft"
    for d in ("saves", "config", "mods", "shaderpacks"):
        (game / d).mkdir(parents=True)
    (out / "private-game.txt").write_text(str(game) + "\n")
    lab.shared.world_marker()
    with (src / "session.lock").open("r+b") as h:
        fcntl.lockf(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = base.copy_world(src, game / "saves" / lab.WORLD)
    world = game / "saves" / lab.WORLD
    base.require(base.tree(world) == manifest, "clone differs")
    marker = lab.pairs((world / "aqualumen-world.properties").read_bytes())
    base.require(marker.get("world_id") == lab.WORLD_ID and marker.get("seed") == "308060", "marker")
    base.require(base.nbt(gzip.decompress((world / "level.dat").read_bytes()))["Data"]["WorldGenSettings"]["seed"] == 308060, "seed")
    base.require(not (world / "playerdata" / PLAYER_FILE).exists() and not (world / "datapacks" / PACK_NAME).exists(), "fixture residue")
    snap_digest = SITE["snapshot"]["sourceDigest"]
    for n in sorted(lab.NORMAL_MODS):
        shutil.copy(orig / "mods" / n, game / "mods")
    shutil.copy(pack, game / "shaderpacks")
    base.require(sha(game / "shaderpacks" / pack.name) == pack_sha, "pack copy")
    for n in ("sodium-options.json", "iris.properties"):
        shutil.copy(orig / "config" / n, game / "config")
    iris = game / "config/iris.properties"
    iris.write_bytes(lab.replace_values(iris.read_bytes(), {"shaderPack": pack.name}, "="))
    options = dict(lab.OPTIONS, maxFps="120", overrideWidth=str(WIDTH), overrideHeight=str(HEIGHT), pauseOnLostFocus="false",
                   chatVisibility="2", fov="0.0", fovEffectScale="0.0", bobView="false", fullscreen="false")
    (game / "options.txt").write_bytes(lab.replace_values((orig / "options.txt").read_bytes(), options, ":"))
    kit = world / "datapacks" / PACK_NAME
    for rel, text in files.items():
        p = kit / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    plan = dict(site="site.json", siteSha256=sha(HERE / "site.json"), pack=pack.name, packSha256=pack_sha, items=items,
                stills=STILLS, clips=CLIPS, timing=dict(periodTicks=PERIOD, checkTicks=CHECK, settle=SETTLE, dwell=DWELL, pair=PAIR, clipTicks=CLIP_TICKS),
                forceloadBox=box, datapackDigest=base.digest({k: base.sha(v.encode()) for k, v in files.items()}),
                world=dict(name=lab.WORLD, worldId=lab.WORLD_ID, seed=308060, sourceDigest=base.digest(manifest),
                           sameAsSiteSnapshot=base.digest(manifest) == snap_digest),
                options=options, playerUuid=PLAYER_UUID, size=[WIDTH, HEIGHT],
                scripts={n: sha(HERE / n) for n in ("campaign.py", "choose.py", "sitesearch.py")})
    (out / "plan.json").write_text(json.dumps(plan, indent=2, default=list))
    env = dict(os.environ, DISPLAY=":1", XDG_RUNTIME_DIR="/run/user/1000", __GLX_VENDOR_LIBRARY_NAME="nvidia", ALSOFT_DRIVERS="null",
               XDG_CACHE_HOME=str(parent / "cache"))
    for k in ("JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "GALLIUM_DRIVER", "LIBGL_KOPPER_DRI2", "VK_DRIVER_FILES"):
        env.pop(k, None)
    java = [runtime["java"], "-Xms512m", "-Xmx3000m", "-XX:ActiveProcessorCount=4", "-Dorg.lwjgl.openal.libname=libopenal.so.1",
            "-cp", ":".join(runtime["cp"]), "net.fabricmc.loader.impl.launch.knot.KnotClient", "--username", PLAYER, "--version", "1.21.1",
            "--gameDir", str(game), "--assetsDir", str(orig.parents[2] / "assets"), "--assetIndex", "17", "--uuid", PLAYER_UUID,
            "--accessToken", "0", "--userType", "legacy", "--width", str(WIDTH), "--height", str(HEIGHT), "--quickPlaySingleplayer", lab.WORLD]
    log = out / "client.log"
    results, skipped, retries, lights = {}, [], [], {}
    p = None
    private = parent / "frames"
    private.mkdir()

    def window():
        r = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid", str(p.pid), "--name", "Minecraft"], env=env, text=True, capture_output=True)
        return r.stdout.strip() if r.returncode == 0 and len(r.stdout.split()) == 1 else None

    def grab(wid, target):
        subprocess.run(["ffmpeg", "-v", "error", "-n", "-f", "x11grab", "-window_id", wid, "-i", env["DISPLAY"], "-frames:v", "1", "-threads", "1", str(target)],
                       env=env, check=True, timeout=8)
        base.require(base.png_size(target) == (WIDTH, HEIGHT), "frame size %s" % (base.png_size(target),))

    def fatal(text):
        low = text.lower()
        if "disabling shaders" in low or "reverting to default" in low:
            return "Iris shader fallback"
        m = re.search(r"\[Render thread/ERROR\]|/ERROR\].*(aqlf:|function|LeafForest)", text)
        if m:
            return text[text.rfind("\n", 0, m.start()) + 1:text.find("\n", m.start())][:300]
        for k, r, _ in evs(text):
            if k in ("ABORT", "FAIL"):
                return "fixture %s %s" % (k, r)
        return None

    def evs(text, start=0):
        o = []
        for m in EVENT_RE.finditer(text, start):
            e = text.find("\n", m.end())
            o.append((m.group(1), m.group(2), len(text) if e < 0 else e))
        return o

    with log.open("xb") as stream:
        p = subprocess.Popen(java, stdout=stream, stderr=stream, env=env, cwd=game)
        status({"runs": {name: dict(state="client-loading", pid=p.pid)}})
        try:
            deadline = time.monotonic() + 900
            while not (live := LIVE_RE.search(t := log.read_text(errors="replace"))):
                base.require(fatal(t) is None, str(fatal(t)))
                base.require(p.poll() is None and time.monotonic() < deadline, "client never reached a live world render")
                time.sleep(.5)
            renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t)
            base.require(renderer and lab.nvidia(renderer.group(1)), "not NVIDIA")
            base.require("Using shaderpack: " + pack.name in t, "pack not selected")
            ready_at, cursor = time.monotonic(), live.end()
            status({"runs": {name: dict(state="capturing", liveAfterSeconds=round(time.time() - t_start, 1), renderer=renderer.group(1).strip())}})
            hud_hidden = False
            cycle = (len(STILLS) * PERIOD + len(CLIPS) * (CHECK + CLIP_TICKS + 60)) / 20
            deadline = ready_at + SETTLE + 2.5 * cycle + 60
            while len(results) < len(items):
                t = log.read_text(errors="replace")
                base.require(fatal(t) is None, str(fatal(t)))
                base.require(p.poll() is None and time.monotonic() < deadline, "items not captured: " + ",".join(x for x in items if x not in results))
                for k, r, _ in evs(t):
                    if k == "LIGHT":
                        nm, lv = r.rsplit("-l", 1)
                        lights[nm] = int(lv)
                new = [e for e in evs(t, cursor) if e[0] == "READY"]
                if not new:
                    time.sleep(.3)
                    continue
                kind, iname, end = new[0]
                cursor = end
                seen = time.monotonic()
                if seen < ready_at + SETTLE or iname in results:
                    skipped.append(dict(item=iname, reason="settle" if iname not in results else "done"))
                    continue
                wid = window()
                base.require(wid is not None, "window not found")
                subprocess.run(["xdotool", "windowfocus", "--sync", wid], env=env, check=True, timeout=4)
                focus = subprocess.check_output(["xdotool", "getwindowfocus"], env=env, text=True).strip()
                base.require(focus == wid, "focus")
                if not hud_hidden:
                    subprocess.run(["xdotool", "key", "--window", wid, "F1"], env=env, check=True, timeout=4)
                    hud_hidden = True
                is_clip = iname in dict(CLIPS)
                if is_clip:
                    clip = out / (iname + ".mp4")
                    subprocess.run(["ffmpeg", "-v", "error", "-n", "-f", "x11grab", "-framerate", "30", "-window_id", wid, "-i", env["DISPLAY"],
                                    "-t", "%.2f" % (CLIP_TICKS / 20 - .4), "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
                                    "-threads", "2", str(clip)], env=env, check=True, timeout=CLIP_TICKS / 20 + 20)
                    after = [e for e in evs(log.read_text(errors="replace"), end) if e[0] in ("DRIFT", "FAIL", "ABORT") and e[1] == iname]
                    if after:
                        clip.rename(out / (iname + "-invalid-%d.mp4" % len(retries)))
                        retries.append(dict(item=iname, events=[e[:2] for e in after]))
                        base.require(len(retries) <= 6, "too many invalidated captures")
                        continue
                    results[iname] = dict(file=clip.name, sha256=sha(clip), secondsAfterReady=round(time.monotonic() - seen, 2), kind="clip",
                                          note="server tp every tick (20 Hz pose steps), recorded at 30 fps by x11grab")
                else:
                    time.sleep(max(0.0, seen + DWELL - time.monotonic()))
                    a, b = private / ("%s-%d-a.png" % (iname, len(retries))), private / ("%s-%d-b.png" % (iname, len(retries)))
                    grab(wid, a)
                    time.sleep(PAIR)
                    grab(wid, b)
                    done = time.monotonic()
                    time.sleep(.5)
                    after = [e for e in evs(log.read_text(errors="replace"), end) if e[0] in ("BEGIN", "DRIFT", "FAIL", "ABORT")]
                    if after:
                        retries.append(dict(item=iname, events=[e[:2] for e in after]))
                        base.require(len(retries) <= 6, "too many invalidated captures")
                        continue
                    target = out / (iname + ".png")
                    shutil.copyfile(a, target)
                    shutil.copyfile(b, out / (iname + "-pair.png"))
                    ra, rb = base.rgb(a, env), base.rgb(b, env)
                    variant, pname = iname.split("--")
                    info = dict(file=target.name, sha256=sha(target), pairSha256=sha(b), secondsAfterReady=round(done - seen, 2),
                                pairMeanAbsDiff=base.mean_abs_diff(ra, rb), frameMean=[round(sum(ra[c::3]) / (WIDTH * HEIGHT), 3) for c in range(3)],
                                skyBandPairMeanAbsDiff=base.mean_abs_diff(ra[:WIDTH * 3 * 120], rb[:WIDTH * 3 * 120]),
                                patches=[dict(rect=s["rect"], nDotL=s["nDotL"], mean=patch_stats(ra, s["rect"]), pairMean=patch_stats(rb, s["rect"]))
                                         for s in pose_of(pname)["patches"]])
                    results[iname] = info
                    status({"runs": {name: dict(captured=len(results), of=len(items), last=iname)}})
                    print(iname, json.dumps([q["mean"] for q in info["patches"]]), info["pairMeanAbsDiff"], flush=True)
                (out / "progress.json").write_text(json.dumps(dict(results=results, lights=lights, retries=retries), indent=2))
        finally:
            wid = window() if p.poll() is None else None
            if wid:
                subprocess.run(["/tmp/aqualumen-wm-close", hex(int(wid))], env=env, timeout=8)
            try:
                p.wait(timeout=40)
            except subprocess.TimeoutExpired:
                p.terminate()
                p.wait(timeout=15)
    t = log.read_text(errors="replace")
    for k, r, _ in evs(t):
        if k == "LIGHT":
            nm, lv = r.rsplit("-l", 1)
            lights[nm] = int(lv)
    renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t).group(1).strip()
    base.require(lab.nvidia(renderer) and "All dimensions are saved" in t, "clean NVIDIA shutdown not logged")
    base.require(base.tree(src) == manifest, "SOURCE WORLD CHANGED")
    for n, h in originals.items():
        base.require(sha(orig / n) == h, "original Lab file changed: " + n)
    base.require({n: sha(orig / "mods" / n) for n in sorted(lab.NORMAL_MODS)} == mods, "mods changed")
    base.require(sha(pack) == pack_sha, "PACK ARCHIVE CHANGED")
    comp = dict(renderer=renderer, glVersion=next((m.group(1).strip() for m in re.finditer(r"OpenGL Version: ([^\n]+)", t)), None),
                pack=pack.name, sha256=pack_sha, packUnchanged=True, normalModFiles=mods,
                world=dict(name=lab.WORLD, worldId=lab.WORLD_ID, seed=308060, sourceDigest=base.digest(manifest), sourceUnchanged=True),
                originalLabFilesUnchanged=sorted(originals), size=[WIDTH, HEIGHT], fovVertical=70, items=items, results=results,
                frontCellLightLevel=lights, skippedHandshakes=skipped, invalidatedCaptures=retries, privateClone=str(game),
                wallSeconds=round(time.time() - t_start, 1), shaderFallback=False,
                note="ordinary client frames (x11grab, display-referred sRGB8); not GPU readback; instrumented private world, not uninstrumented play")
    (out / "complete.json").write_text(json.dumps(comp, indent=2))
    status({"runs": {name: dict(state="complete", finished=time.strftime("%H:%M:%S"), wallSeconds=comp["wallSeconds"],
                                frontCellLightLevel=lights, summary=summary(results))}})
    lock.close()
    return comp


def summary(results):
    out = {}
    for k, v in results.items():
        if v.get("patches"):
            m = [sum(q["mean"][c] for q in v["patches"]) / len(v["patches"]) for c in range(3)]
            out[k] = dict(patchMeanRGB=[round(x, 1) for x in m], pairDiff=v["pairMeanAbsDiff"])
    return out


def compare(a, b):
    ca, cb = (json.loads((HERE / r / "complete.json").read_text()) for r in (a, b))
    outdir = HERE / ("compare-%s-vs-%s" % (a, b))
    outdir.mkdir()
    rows = []
    for item, va in ca["results"].items():
        vb = cb["results"].get(item)
        if not vb or va.get("kind") == "clip":
            continue
        ma, mb = summary({item: va})[item]["patchMeanRGB"], summary({item: vb})[item]["patchMeanRGB"]
        rows.append(dict(item=item, before=ma, after=mb))
        subprocess.run(["ffmpeg", "-v", "error", "-n", "-i", str(HERE / a / va["file"]), "-i", str(HERE / b / vb["file"]), "-filter_complex",
                        "[0][1]hstack=inputs=2,scale=1600:-2", "-q:v", "3", str(outdir / (item + ".jpg"))], check=True)
    (outdir / "patches.json").write_text(json.dumps(dict(before=ca["pack"], after=cb["pack"], rows=rows), indent=2))
    status({"comparisons": {outdir.name: dict(rows=len(rows))}})


def campaign():
    lockf = open(CAMPAIGN_LOCK, "a+b")
    fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)  # never stack two campaigns
    status(dict(owner="Claude Opus (forest leaf scene/visual advisor)", phase="baseline", pid=os.getpid(),
                parentOwns=["1440p timing", "supplemental native QA", "final install", "player experience"]))
    if not (HERE / "base-r1").exists():
        run(BASE_PACK, "base-r1")
    status(dict(phase="waiting-rc1", waitingFor=str(RC1)))
    t0 = time.time()
    while not RC1.is_file():
        base.require(time.time() - t0 < 6 * 3600, "rc1 never appeared")
        time.sleep(30)
    time.sleep(20)  # let the writer finish
    s1 = sha(RC1)
    time.sleep(10)
    base.require(sha(RC1) == s1, "rc1 still changing")
    status(dict(phase="rc1"))
    if not (HERE / "rc1-r1").exists():
        run(RC1, "rc1-r1")
    compare("base-r1", "rc1-r1")
    status(dict(phase="complete"))


if __name__ == "__main__":
    cmd = sys.argv[1:]
    if cmd == ["dry"]:
        files, items, box = datapack()
        check(files, items)
        d = Path(tempfile.mkdtemp(prefix="aql-leaf-forest-dry-"))
        for rel, text in files.items():
            q = d / rel
            q.parent.mkdir(parents=True, exist_ok=True)
            q.write_text(text)
        print("dry ok", d, len(files), "items", len(items), "box", box)
    elif cmd[:1] == ["run"] and len(cmd) == 3:
        run(cmd[1], cmd[2])
    elif cmd[:1] == ["compare"] and len(cmd) == 3:
        compare(cmd[1], cmd[2])
    elif cmd == ["campaign"]:
        campaign()
    else:
        sys.exit(__doc__)
