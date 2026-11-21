"""Native one-bounce optical fixture: ordinary client (three normal mods, no recorder Mod) in a
private, exact-UUID/seed copy of the Lab world. Geometry lives in fixture.py.

    python3 capture.py <shaderpack.zip> <role-dir>     # real run (Codex only; NVIDIA, DISPLAY :1)
    python3 capture.py --dry-run                       # no lock, no world, no launch
    AQL_INDIRECT_ROLES=red,neutral,wide-red python3 capture.py ...   # optional subset

The datapack cycles all selected roles forever. Each scene: say BEGIN -> rebuild mutable cells and
teleport -> after CHECK ticks verify every one of the 1512 reserved cells, the player pose/mode and an
entity-free room, then say READY (or FAIL) -> re-verify every 10 ticks, saying DRIFT on any change.
A READY only counts when it is logged after the client reported a live world render plus SETTLE
seconds; a capture is discarded (and retried next cycle) if BEGIN/DRIFT follows its READY before the
second frame is taken.
"""

import fcntl
import gzip
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import fixture as F  # noqa: E402

LOCK = "/tmp/aql-render21-1000.lock"
PLAYER_UUID = "00000000000040008000000000000421"
PLAYER_FILE = "00000000-0000-4000-8000-000000000421.dat"
SEED = 308060
PACK_NAME = "IndirectLight"
NS = "aqi"
PERIOD = 200  # ticks per scene
CHECK = 60  # ticks after scene start before the verified handshake
SETTLE = 6.0  # seconds after client render readiness before any READY counts
DWELL = 3.0  # seconds after READY before the first frame
PAIR = 0.6  # seconds between the two frames of a stability pair
READY_RE = re.compile(r"\[Render thread/INFO\]: .*\[Aqualumen Physics\] .*bridge initialized")
EVENT_RE = re.compile(r"\[Server\] AQI_(READY|FAIL|DRIFT|BEGIN|ABORT|BUILT)_([a-z0-9-]+)_END")
ERROR_RE = re.compile(r"\[Render thread/ERROR\]|/ERROR\].*(aqi:|function|IndirectLight)")


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def selected_roles(env=os.environ):
    raw = env.get("AQL_INDIRECT_ROLES", "").strip()
    if not raw:
        return list(F.ROLE_NAMES)
    names = [n.strip() for n in raw.split(",") if n.strip()]
    require(len(set(names)) == len(names), "Duplicate role in AQL_INDIRECT_ROLES")
    unknown = sorted(set(names) - set(F.ROLE_NAMES))
    require(not unknown, "Unknown roles: " + ",".join(unknown))
    return [n for n in F.ROLE_NAMES if n in names]


# ---------------------------------------------------------------- datapack (pure)


def w(p):
    return " ".join(str(v) for v in F.world(p))


def fill(b, block):
    (lo, hi) = b
    return "fill %s %s %s" % (w(lo), w(tuple(v - 1 for v in hi)), block)


MUTABLE = [F.EAST_BOX, F.LAMP_BOX, F.FIRST_BOX, F.SECOND_BOX]


def mutable(cell):
    return any(all(lo[a] <= cell[a] < hi[a] for a in range(3)) for lo, hi in MUTABLE)


def wrap(a):
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def pose_selector(pose):
    yaw, pitch = pose["yaw"], pose["pitch"]
    return "@a[name=%s,distance=..0.01,gamemode=spectator,x_rotation=%s..%s,y_rotation=%s..%s]" % (
        F.PLAYER,
        F.fmt(pitch - 0.05),
        F.fmt(pitch + 0.05),
        F.fmt(wrap(yaw - 0.05)),
        F.fmt(wrap(yaw + 0.05)),
    )


def tp(pose):
    return "tp %s %s %s %s" % (
        F.PLAYER,
        " ".join(F.fmt(v) for v in F.feet(pose)),
        F.fmt(pose["yaw"]),
        F.fmt(pose["pitch"]),
    )


def count(cell, block):
    return "execute if block %s %s run scoreboard players add #n %s 1" % (w(cell), block, NS)


def datapack(roles):
    """Return {relative path: text} for the world-local datapack."""
    lo, hi = F.LO, F.HI
    lo_w, hi_w = F.world(lo), F.world(hi)
    files = {
        "pack.mcmeta": json.dumps(
            {"pack": {"pack_format": 48, "description": "Private Aqualumen one-bounce fixture"}}
        ),
        "data/minecraft/tags/function/tick.json": json.dumps({"values": [NS + ":tick"]}),
    }
    fn = {}
    fn["tick"] = ["execute as @a[name=%s,tag=!aqi_started] run function %s:start" % (F.PLAYER, NS)]
    fn["start"] = [
        "tag @s add aqi_started",
        "gamerule doDaylightCycle false",
        "gamerule doWeatherCycle false",
        "gamerule doMobSpawning false",
        "gamerule randomTickSpeed 0",
        "gamerule doFireTick false",
        "gamerule sendCommandFeedback false",
        "gamerule commandBlockOutput false",
        "gamerule announceAdvancements false",
        "difficulty peaceful",
        "weather clear",
        "time set 18000",
        "gamemode spectator @s",
        "scoreboard objectives add %s dummy" % NS,
        "scoreboard players set #attempt %s 0" % NS,
        "scoreboard players set #built %s 0" % NS,
        "forceload add %d %d %d %d" % (lo_w[0], lo_w[2], hi_w[0], hi_w[2]),
        tp(F.POSES[F.role(roles[0])["pose"]]),
        "schedule function %s:setup 20t replace" % NS,
    ]
    corners = [(x, lo_w[1], z) for x in (lo_w[0], hi_w[0]) for z in (lo_w[2], hi_w[2])]
    loaded = " ".join("if loaded %d %d %d" % c for c in corners)
    fn["setup"] = [
        "scoreboard players add #attempt %s 1" % NS,
        "scoreboard players set #loaded %s 0" % NS,
        "execute %s run scoreboard players set #loaded %s 1" % (loaded, NS),
        "execute if score #loaded %s matches 0 if score #attempt %s matches ..60 run schedule function %s:setup 20t replace"
        % (NS, NS, NS),
        "execute if score #loaded %s matches 0 if score #attempt %s matches 61.. run say AQI_ABORT_unloaded_END"
        % (NS, NS),
        "execute if score #loaded %s matches 1 if score #built %s matches 0 run function %s:reserve" % (NS, NS, NS),
    ]
    # Count AIR positively: an unloaded or non-air cell can never be counted as clear.
    reserve = ["scoreboard players set #n %s 0" % NS]
    reserve += [count(c, F.AIR) for c in sorted(F.cells(F.role(roles[0])))]
    reserve += [
        "execute if score #n %s matches %d run function %s:build" % (NS, F.CELLS, NS),
        "execute unless score #n %s matches %d run say AQI_ABORT_reserved_END" % (NS, F.CELLS),
    ]
    fn["reserve"] = reserve
    build = ["scoreboard players set #built %s 1" % NS]
    build += [fill(b, block) for b, block in F.SHELL]
    build += ["say AQI_BUILT_fixture_END", "schedule function %s:s0 20t replace" % NS]
    fn["build"] = build
    static = F.cells(F.role(roles[0]))
    fn["vstatic"] = [count(c, b) for c, b in sorted(static.items()) if not mutable(c)]
    n = len(roles)
    # dx/dy/dz select [pos, pos + d + 1): exactly the 14x9x12 reserved cells.
    room = "positioned %s unless entity @e[type=!minecraft:player,dx=%d,dy=%d,dz=%d]" % (
        w(lo),
        hi[0] - lo[0],
        hi[1] - lo[1],
        hi[2] - lo[2],
    )
    for i, name in enumerate(roles):
        r = F.role(name)
        pose = F.POSES[r["pose"]]
        grid = F.cells(r)
        assert all(grid[c] == b for c, b in static.items() if not mutable(c))
        scene = ["schedule clear %s:h%d" % (NS, j) for j in range(n)]
        scene += ["say AQI_BEGIN_%s_END" % name, "time set 18000", "weather clear"]
        # The two baffles share cells (10, 0..6, 2): clear absent ones first, then place present ones.
        baffles = [(F.FIRST_BOX, r["first"]), (F.SECOND_BOX, r["second"])]
        scene += [fill(F.EAST_BOX, F.EAST[r["east"]])]
        scene += [fill(b, F.AIR) for b, on in baffles if not on]
        scene += [fill(b, F.BLACK) for b, on in baffles if on]
        scene += [
            "setblock %s %s" % (w(F.LAMP_CELL), F.LAMP[r["lamp"]]),
            tp(pose),
            "schedule function %s:c%d %dt replace" % (NS, i, CHECK),
            "schedule function %s:s%d %dt replace" % (NS, (i + 1) % n, PERIOD),
        ]
        fn["s%d" % i] = scene
        fn["v%d" % i] = (
            ["scoreboard players set #n %s 0" % NS, "scoreboard players set #ok %s 0" % NS]
            + ["function %s:vstatic" % NS]
            + [count(c, b) for c, b in sorted(grid.items()) if mutable(c)]
            + [
                "execute if score #n %s matches %d %s positioned %s if entity %s run scoreboard players set #ok %s 1"
                % (NS, F.CELLS, room, " ".join(F.fmt(v) for v in F.feet(pose)), pose_selector(pose), NS)
            ]
        )
        fn["c%d" % i] = [
            "function %s:v%d" % (NS, i),
            "execute if score #ok %s matches 1 run say AQI_READY_%s_END" % (NS, name),
            "execute if score #ok %s matches 0 run say AQI_FAIL_%s_END" % (NS, name),
            "schedule function %s:h%d 10t replace" % (NS, i),
        ]
        fn["h%d" % i] = [
            "function %s:v%d" % (NS, i),
            "execute if score #ok %s matches 0 run say AQI_DRIFT_%s_END" % (NS, name),
            "schedule function %s:h%d 10t replace" % (NS, i),
        ]
    assert CHECK + 10 < PERIOD
    for k, lines in fn.items():
        files["data/%s/function/%s.mcfunction" % (NS, k)] = "\n".join(lines) + "\n"
    return files


def check_datapack(files, roles):
    """Static validation of generated commands (bounds, counts, markers)."""
    lo_w, hi_w = F.world(F.LO), F.world(F.HI)
    coord = re.compile(r"(?:block|fill|setblock|loaded) (-?\d+) (-?\d+) (-?\d+)")
    for path, text in files.items():
        for line in text.splitlines():
            for m in coord.finditer(line):
                x, y, z = map(int, m.groups())
                require(
                    lo_w[0] <= x <= hi_w[0] and lo_w[1] <= y <= hi_w[1] and lo_w[2] <= z <= hi_w[2],
                    "Command writes or tests outside the reserved volume: " + line,
                )
    fdir = "data/%s/function/" % NS
    reserve = files[fdir + "reserve.mcfunction"].splitlines()
    require(sum("minecraft:air run" in l for l in reserve) == F.CELLS, "reserve does not cover every cell")
    static = files[fdir + "vstatic.mcfunction"].splitlines()
    for i, name in enumerate(roles):
        v = files[fdir + "v%d.mcfunction" % i].splitlines()
        require(len(static) + sum(l.startswith("execute if block") for l in v) == F.CELLS, name)
        require("AQI_READY_%s_END" % name in files[fdir + "c%d.mcfunction" % i], name)
    for k in ("reserve", "build"):
        require("tp " not in files[fdir + k + ".mcfunction"], "setup teleports")
    # fill/setblock may only appear in build and scene functions
    for path, text in files.items():
        name = path.rsplit("/", 1)[-1]
        if re.search(r"^(fill|setblock) ", text, re.M):
            require(name == "build.mcfunction" or re.fullmatch(r"s\d+\.mcfunction", name), path)


def simulate(files, roles, cycles=2):
    """Execute build + scene fill/setblock/tp on an all-air grid and compare every cell and pose
    with fixture.cells()/POSES, and every v<i> count line with the simulated block, in cycle order
    (twice, so every role is also entered from its cycle predecessor)."""
    fdir = "data/%s/function/" % NS
    origin = F.world(F.LO)
    grid = {F.world(c): F.AIR for c in F.cells(F.role(roles[0]))}
    num = r"(-?[\d.]+)"
    fill_re = re.compile(r"^fill (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (\S+)$")
    set_re = re.compile(r"^setblock (-?\d+) (-?\d+) (-?\d+) (\S+)$")
    tp_re = re.compile(r"^tp %s %s %s %s %s %s$" % (F.PLAYER, num, num, num, num, num))
    count_re = re.compile(r"^execute if block (-?\d+) (-?\d+) (-?\d+) (\S+) run scoreboard")
    player = None

    def run(name):
        nonlocal player
        for line in files[fdir + name + ".mcfunction"].splitlines():
            if m := fill_re.match(line):
                a = list(map(int, m.groups()[:6]))
                for x in range(a[0], a[3] + 1):
                    for y in range(a[1], a[4] + 1):
                        for z in range(a[2], a[5] + 1):
                            require((x, y, z) in grid, "fill outside fixture")
                            grid[x, y, z] = m.group(7)
            elif m := set_re.match(line):
                c = tuple(map(int, m.groups()[:3]))
                require(c in grid, "setblock outside fixture")
                grid[c] = m.group(4)
            elif m := tp_re.match(line):
                player = tuple(map(float, m.groups()))

    run("build")
    built = {F.world(c): (F.AIR if mutable(c) else b) for c, b in F.cells(F.role(roles[0])).items()}
    require(grid == built, "build does not produce the static shell with empty mutable cells")
    for _ in range(cycles):
        for i, name in enumerate(roles):
            run("s%d" % i)
            r = F.role(name)
            want = {F.world(c): b for c, b in F.cells(r).items()}
            bad = [c for c in grid if grid[c] != want[c]]
            require(not bad, "%s: simulated cells differ, e.g. %s" % (name, bad[:3]))
            pose = F.POSES[r["pose"]]
            require(
                player is not None
                and max(abs(a - b) for a, b in zip(player[:3], F.feet(pose))) < 1e-9
                and (player[3], player[4]) == (pose["yaw"], pose["pitch"]),
                name + ": teleport pose",
            )
            lines = files[fdir + "vstatic.mcfunction"].splitlines()
            lines += files[fdir + "v%d.mcfunction" % i].splitlines()
            hits = [m for m in map(count_re.match, lines) if m]
            require(len(hits) == F.CELLS, name + ": verification cell count")
            require(
                len({tuple(map(int, m.groups()[:3])) for m in hits}) == F.CELLS
                and all(grid[tuple(map(int, m.groups()[:3]))] == m.group(4) for m in hits),
                name + ": verification expects a different block than the scene builds",
            )
    return origin


# ---------------------------------------------------------------- plan (pure)


def expectations():
    t = json.loads((HERE / "transport.json").read_text())
    mean = lambda rows, c: sum(r[c] for r in rows) / len(rows)
    red, neu = t["redWarm"], t["neutralWarm"]
    return dict(
        source="transport.json (offline one-bounce integral, no ambient, no multi-bounce)",
        redOverNeutralRed=round(mean(red, 0) / mean(neu, 0), 3),
        redChroma=round(mean(red, 0) / mean(red, 1), 2),
        neutralChroma=round(mean(neu, 0) / mean(neu, 1), 2),
        blackOverRedLuma=round(
            sum(mean(t["blackWarm"], c) * k for c, k in enumerate((0.2126, 0.7152, 0.0722)))
            / sum(mean(red, c) * k for c, k in enumerate((0.2126, 0.7152, 0.0722))),
            4,
        ),
        soulOverWarmRed=round(mean(t["redSoul"], 0) / mean(red, 0), 3),
        receiverProfile=[round(v / t["quadrature64"][1], 3) for v in t["quadrature64"]],
        firstLegBlocked=t["firstLegBlocked"],
        secondLegBlocked=t["secondLegBlocked"],
    )


ROLE_EXPECT = {
    "red": "warm/red one-bounce tint on all three patches; centre patch brightest",
    "neutral": "same geometry, roughly neutral bounce; red channel well below `red`",
    "black": "near `off` (black face reflects ~0.2% of red-face luma in the reference)",
    "off": "no lamp: residual only (ambient floor / shader minimum light)",
    "first-block": "one-bounce removed by geometry: should approach `off`",
    "second-block": "one-bounce removed by geometry: should approach `off`",
    "soul": "cyan emitter on red face: far weaker red bounce than `red`",
    "moved": "same receivers from a moved/rotated camera: patch means should match `red`",
    "red-repeat": "after every toggle: should reproduce `red` (stability/hysteresis check)",
    "wide-red": "user-facing side view: lit red east face, hood, white receiver wall",
    "wide-neutral": "same side view with polished deepslate face",
}


def plan(roles):
    rows = []
    for name in roles:
        r = F.role(name)
        row = dict(
            r,
            eastBlock=F.EAST[r["east"]],
            lampBlock=F.LAMP[r["lamp"]],
            camera=F.pose_record(r["pose"]),
            expectation=ROLE_EXPECT[name],
        )
        if r["pose"] != "wide":
            row["samples"] = F.samples(r)
        rows.append(row)
    boxes = lambda bs: [dict(world=[list(F.world(lo)), list(F.world(tuple(v - 1 for v in hi)))], local=[lo, hi]) for lo, hi in bs]
    return dict(
        fixture="reports/2026-11-21-indirect-light/fixture.py",
        reference="reports/2026-11-21-indirect-light/reference.py",
        origin=F.ORIGIN,
        reservedCells=dict(local=[F.LO, F.HI], world=[F.world(F.LO), F.world(F.HI)], count=F.CELLS),
        boxes=dict(
            east=boxes([F.EAST_BOX]),
            lamp=boxes([F.LAMP_BOX]),
            firstLeg=boxes([F.FIRST_BOX]),
            secondLeg=boxes([F.SECOND_BOX]),
            shell=[dict(block=b, **boxes([bb])[0]) for bb, b in F.SHELL],
        ),
        translation=(
            "baffles shifted from reference z=1 to z>=2 so the receiver camera (eye z=1.85) is in air; "
            "fixture.crosscheck() re-runs reference.transport with the native boxes: exactly zero"
        ),
        sampleMethod=(
            "Minecraft perspective: vertical fov %d deg, aspect %d/%d, fovEffectScale 0, bobView off, "
            "spectator eye = feet + %.2f; window pixel edges at integers, v down. patch = [x0,y0,x1,y1) "
            "%dx%d around floor(projected); every patch corner and the centre ray first-hit the white "
            "receiver face z=0 in every role (ray cast against all solids)"
            % (F.FOV, F.WIDTH, F.HEIGHT, F.EYE, F.PATCH, F.PATCH)
        ),
        timing=dict(periodTicks=PERIOD, checkTicks=CHECK, settleSeconds=SETTLE, dwellSeconds=DWELL, pairSeconds=PAIR),
        expectations=expectations(),
        roles=rows,
    )


# ---------------------------------------------------------------- world helpers


def nbt(data):
    pos = 0

    def take(n):
        nonlocal pos
        pos += n
        return data[pos - n : pos]

    def payload(tag):
        if tag == 1:
            return struct.unpack(">b", take(1))[0]
        if tag == 2:
            return struct.unpack(">h", take(2))[0]
        if tag == 3:
            return struct.unpack(">i", take(4))[0]
        if tag == 4:
            return struct.unpack(">q", take(8))[0]
        if tag == 5:
            return struct.unpack(">f", take(4))[0]
        if tag == 6:
            return struct.unpack(">d", take(8))[0]
        if tag in (7, 11, 12):
            n = struct.unpack(">i", take(4))[0]
            take(n * {7: 1, 11: 4, 12: 8}[tag])
            return None
        if tag == 8:
            return take(struct.unpack(">H", take(2))[0]).decode("utf-8", "replace")
        if tag == 9:
            kind, n = struct.unpack(">bi", take(5))
            return [payload(kind) for _ in range(n)]
        if tag == 10:
            out = {}
            while (kind := take(1)[0]) != 0:
                key = take(struct.unpack(">H", take(2))[0]).decode("utf-8", "replace")
                out[key] = payload(kind)
            return out
        raise RuntimeError("Bad NBT tag %d" % tag)

    require(take(1)[0] == 10, "level.dat root is not a compound")
    take(struct.unpack(">H", take(2))[0])
    return payload(10)


def tree(folder, skip=("session.lock",)):
    out = {}
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder).as_posix()
        require(not path.is_symlink(), "Symlink in world tree: " + rel)
        if path.is_file() and rel not in skip:
            out[rel] = sha(path.read_bytes())
    return out


def copy_world(src, dst):
    manifest = {}
    dst.mkdir()
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src).as_posix()
        require(not path.is_symlink(), "Symlink in world tree: " + rel)
        if rel == "session.lock":
            continue
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        data = path.read_bytes()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as f:
            f.write(data)
        manifest[rel] = sha(data)
    return manifest


def digest(manifest):
    return sha(json.dumps(manifest, sort_keys=True).encode())


# ---------------------------------------------------------------- image helpers


def png_size(path):
    head = path.read_bytes()[:24]
    require(head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR", "Not a PNG: " + path.name)
    return struct.unpack(">II", head[16:24])


def rgb(path, env):
    return subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:"],
        env=env,
        check=True,
        capture_output=True,
        timeout=10,
    ).stdout


def patch_mean(raw, rect):
    x0, y0, x1, y1 = rect
    acc = [0, 0, 0]
    for y in range(y0, y1):
        row = raw[(y * F.WIDTH + x0) * 3 : (y * F.WIDTH + x1) * 3]
        for c in range(3):
            acc[c] += sum(row[c::3])
    n = (x1 - x0) * (y1 - y0)
    return [round(a / n, 3) for a in acc]


def mean_abs_diff(a, b, stride=7):
    return round(sum(abs(x - y) for x, y in zip(a[::stride], b[::stride])) / len(a[::stride]), 4)


# ---------------------------------------------------------------- log events


def events(text, start=0):
    """[(kind, role, end offset of line)] for handshake markers after `start`."""
    out = []
    for m in EVENT_RE.finditer(text, start):
        end = text.find("\n", m.end())
        out.append((m.group(1), m.group(2), len(text) if end < 0 else end))
    return out


def fatal(text):
    low = text.lower()
    if "disabling shaders" in low or "reverting to default" in low:
        return "Iris shader fallback"
    m = ERROR_RE.search(text)
    if m:
        return "Error line: " + text[text.rfind("\n", 0, m.start()) + 1 : text.find("\n", m.start())][:300]
    for kind, role, _ in events(text):
        if kind == "ABORT":
            return "Fixture aborted: " + role
        if kind == "FAIL":
            return "Fixture verification failed: " + role
    return None


# ---------------------------------------------------------------- dry run


def dry_run():
    t0 = time.monotonic()
    F.selftest()
    roles = selected_roles()
    files = datapack(roles)
    check_datapack(files, roles)
    simulate(files, roles)
    target = Path(tempfile.mkdtemp(prefix="aql-indirect-dry-"))
    for rel, text in files.items():
        p = target / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    p = plan(roles)
    (target / "plan.json").write_text(json.dumps(p, indent=2))
    # Synthetic log: early READY before readiness must be ignored; fatal markers detected.
    log = (
        "[Server thread/INFO]: [Not Secure] [Server] AQI_READY_red_END\n"
        "[Render thread/INFO]: [STDOUT]: [Aqualumen Physics] 0.2.0 contact bridge initialized (512)\n"
        "[Server thread/INFO]: [Not Secure] [Server] AQI_BEGIN_neutral_END\n"
        "[Server thread/INFO]: [Not Secure] [Server] AQI_READY_red-repeat_END\n"
    )
    ready = READY_RE.search(log)
    require(ready is not None, "readiness regex")
    ev = events(log, ready.end())
    require([(k, r) for k, r, _ in ev] == [("BEGIN", "neutral"), ("READY", "red-repeat")], ev)
    require(fatal(log) is None, "false fatal")
    require(fatal(log + "[Server] AQI_ABORT_reserved_END\n") == "Fixture aborted: reserved", "abort")
    require(fatal(log + "[Render thread/ERROR]: x\n") is not None, "render error")
    require(fatal("[Worker-Main-2/ERROR]: Failed to load function aqi:s0\n") is not None, "function error")
    require(wrap(180.05) == -179.95 and wrap(179.95) == 179.95 and wrap(-180) == 180.0, "wrap")
    raw = bytes(range(256)) * (F.WIDTH * F.HEIGHT * 3 // 256)
    require(len(raw) == F.WIDTH * F.HEIGHT * 3, "raw size")
    patch_mean(raw, p["roles"][0]["samples"][0]["patch"]) if "samples" in p["roles"][0] else None
    total = sum(len(t) for t in files.values())
    print("dry run ok:", target, "| functions", len(files) - 2, "| bytes", total, "| %.1fs" % (time.monotonic() - t0))
    for row in p["roles"]:
        cam = row["camera"]
        line = "%-13s eye %s yaw %g pitch %g" % (row["name"], cam["eyeWorld"], cam["yaw"], cam["pitch"])
        if "samples" in row:
            line += " patches " + json.dumps([s["patch"] for s in row["samples"]])
        print(line)
    return target


# ---------------------------------------------------------------- real run


def main(argv):
    require(len(argv) == 3, "usage: capture.py <shaderpack.zip> <role-dir> | --dry-run")
    require(os.getuid() == 1000, "Fixed lock/runtime paths assume uid 1000")
    roles = selected_roles()
    pack = Path(argv[1])
    require(pack.is_file() and not pack.is_symlink() and pack.suffix == ".zip", "Pack must be a regular .zip")
    pack = pack.resolve()
    photon = os.environ.get("AQL_PHOTON_COLORED") == "1"
    if photon:
        require(sha(pack.read_bytes()) == "1228172bfb0ee49de3d2b6268390bac52c9a57dd0aa92c8903e57cf14583203a",
                "External comparison requires the pinned Photon v1.1 archive")
    ready_pattern = re.compile(r"Creating pipeline for dimension minecraft:overworld.*?\[Render thread/INFO\]: Started [1-9]\d* worker threads", re.S) if photon else READY_RE

    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", argv[2]) is not None, "Role dir must be a simple name")
    out = HERE / argv[2]
    require(out.parent == HERE and not out.exists() and not out.is_symlink(), "Role dir exists or escapes")
    files = datapack(roles)
    check_datapack(files, roles)
    simulate(files, roles)
    the_plan = plan(roles)
    script_hashes = {n: sha((HERE / n).read_bytes()) for n in ("capture.py", "fixture.py")}

    lock = open(LOCK, "a+b")
    fcntl.flock(lock, fcntl.LOCK_EX)
    sys.path.insert(0, str(ROOT / "tools"))
    import ground_shadow_lab as g

    lab = g.lab
    orig = g.GAME.resolve()
    runtime = json.loads((ROOT / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
    assets = orig.parents[2] / "assets"
    src = orig / "saves" / lab.WORLD
    require(src.is_dir() and not src.is_symlink() and src.resolve().parent == orig / "saves", "Source world path")
    require(not str(pack).startswith(str(orig) + os.sep), "Pack must not live inside the Lab instance")
    for helper in ("/tmp/aqualumen-wm-close",):
        require(os.access(helper, os.X_OK), "Missing helper " + helper)
    originals = {
        n: sha((orig / n).read_bytes())
        for n in ("options.txt", "config/iris.properties", "config/sodium-options.json")
        if (orig / n).is_file()
    }
    mods = {n: sha((orig / "mods" / n).read_bytes()) for n in sorted(lab.NORMAL_MODS)}

    out.mkdir()
    labroot = Path(tempfile.mkdtemp(prefix="indirect-optics-", dir=orig.parent)).resolve()
    game = labroot / "Aqualumen Lab/minecraft"
    require(labroot.parent == orig.parent and not str(game).startswith(str(orig) + os.sep), "Clone path")
    game.mkdir(parents=True)
    (out / "private-game.txt").write_text(str(game) + "\n")
    for n in ["shaderpacks", "mods", "config", "saves"]:
        (game / n).mkdir()

    # Exact-UUID source, exclusive session lock while cloning, then verify the private clone.
    lab.shared.world_marker()
    with (src / "session.lock").open("r+b") as f:
        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source_manifest = copy_world(src, game / "saves" / lab.WORLD)
    world = (game / "saves" / lab.WORLD).resolve()
    require(world.parent == game / "saves" and len(list((game / "saves").iterdir())) == 1, "Clone not unique")
    require(tree(world) == source_manifest, "Clone differs from source")
    marker = lab.pairs((world / "aqualumen-world.properties").read_bytes())
    require(marker.get("world_id") == lab.WORLD_ID and marker.get("seed") == str(SEED), "Clone UUID/seed marker")
    level = nbt(gzip.decompress((world / "level.dat").read_bytes()))
    require(level["Data"]["WorldGenSettings"]["seed"] == SEED, "level.dat seed differs")
    require(not (world / "playerdata" / PLAYER_FILE).exists(), "Fixture player already in source world")
    require(not (world / "datapacks" / PACK_NAME).exists(), "Datapack already present")

    for n in sorted(lab.NORMAL_MODS):
        shutil.copy(orig / "mods" / n, game / "mods")
        require(sha((game / "mods" / n).read_bytes()) == mods[n], "Mod copy differs")
    shutil.copy(pack, game / "shaderpacks")
    pack_sha = sha(pack.read_bytes())
    if photon:
        (game / "shaderpacks" / (pack.name + ".txt")).write_text("COLORED_LIGHTS=true\n")

    require(sha((game / "shaderpacks" / pack.name).read_bytes()) == pack_sha, "Pack copy differs")
    for n in ["sodium-options.json", "iris.properties"]:
        if (orig / "config" / n).exists():
            shutil.copy(orig / "config" / n, game / "config")
    iris = game / "config/iris.properties"
    iris.write_bytes(lab.replace_values(iris.read_bytes(), {"shaderPack": pack.name}, "="))
    require(lab.pairs(iris.read_bytes()).get("enableShaders", "true") == "true", "Shaders disabled in config")
    options = dict(
        lab.OPTIONS,
        maxFps="120",
        overrideWidth=str(F.WIDTH),
        overrideHeight=str(F.HEIGHT),
        pauseOnLostFocus="false",
        chatVisibility="2",
        mainHand='"right"',
        fov=F.fmt((F.FOV - 70) / 40),
        fovEffectScale="0.0",
        bobView="false",
    )
    (game / "options.txt").write_bytes(lab.replace_values((orig / "options.txt").read_bytes(), options, ":"))
    kit = world / "datapacks" / PACK_NAME
    for rel, text in files.items():
        p = kit / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    pack_digest = digest({k: sha(v.encode()) for k, v in files.items()})
    the_plan.update(
        pack=pack.name,
        packSha256=pack_sha,
        datapackDigest=pack_digest,
        options=options,
        world=dict(name=lab.WORLD, worldId=lab.WORLD_ID, seed=SEED, sourceDigest=digest(source_manifest)),
        playerUuid=PLAYER_UUID,
    )
    (out / "plan.json").write_text(json.dumps(the_plan, indent=2))

    env = dict(
        os.environ,
        DISPLAY=":1",
        XDG_RUNTIME_DIR="/run/user/1000",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus",
        __GLX_VENDOR_LIBRARY_NAME="nvidia",
        ALSOFT_DRIVERS="null",
        XDG_CACHE_HOME=str(labroot / "cache"),
    )
    for k in ["JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "GALLIUM_DRIVER", "LIBGL_KOPPER_DRI2", "VK_DRIVER_FILES"]:
        env.pop(k, None)
    java = [
        runtime["java"], "-Xms512m", "-Xmx2600m", "-XX:ActiveProcessorCount=4",
        "-Dorg.lwjgl.openal.libname=libopenal.so.1", "-cp", ":".join(runtime["cp"]),
        "net.fabricmc.loader.impl.launch.knot.KnotClient", "--username", F.PLAYER, "--version", "1.21.1",
        "--gameDir", str(game), "--assetsDir", str(assets), "--assetIndex", "17", "--uuid", PLAYER_UUID,
        "--accessToken", "0", "--userType", "legacy", "--width", str(F.WIDTH), "--height", str(F.HEIGHT),
        "--quickPlaySingleplayer", lab.WORLD,
    ]  # fmt: skip
    private = labroot / "frames"
    private.mkdir()
    log = out / "client.log"
    results, order, skipped, retries = {}, [], [], []
    p = None

    def window():
        r = subprocess.run(
            ["xdotool", "search", "--all", "--onlyvisible", "--pid", str(p.pid), "--name", "Minecraft"],
            env=env, text=True, capture_output=True,
        )  # fmt: skip
        return r.stdout.strip() if r.returncode == 0 and len(r.stdout.split()) == 1 else None

    def grab(wid, target):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-n", "-f", "x11grab", "-window_id", wid, "-i", env["DISPLAY"],
             "-frames:v", "1", "-threads", "1", str(target)],
            env=env, check=True, timeout=6,
        )  # fmt: skip
        require(png_size(target) == (F.WIDTH, F.HEIGHT), "Frame size")

    def text():
        return log.read_text(errors="replace")

    with log.open("xb") as stream:
        p = subprocess.Popen(java, stdout=stream, stderr=stream, env=env, cwd=game)
        try:
            deadline = time.monotonic() + 300
            while not (ready := ready_pattern.search(t := text())):
                require(fatal(t) is None, str(fatal(t)))
                require(p.poll() is None and time.monotonic() < deadline, "Client never reached a live world render")
                time.sleep(0.3)
            renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t)
            require(renderer and lab.nvidia(renderer.group(1)), "Not the NVIDIA renderer")
            require("Using shaderpack: " + pack.name in t, "Iris did not select the pack")
            ready_at, cursor = time.monotonic(), ready.end()
            cycle = PERIOD / 20 * len(roles)
            deadline = ready_at + SETTLE + 3 * cycle + 30
            while len(results) < len(roles):
                t = text()
                require(fatal(t) is None, str(fatal(t)))
                require(p.poll() is None and time.monotonic() < deadline, "Roles not captured: " + ",".join(sorted(set(roles) - set(results))))
                new = [e for e in events(t, cursor) if e[0] == "READY"]
                if not new:
                    time.sleep(0.3)
                    continue
                kind, name, end = new[0]
                cursor = end
                seen_at = time.monotonic()
                if seen_at < ready_at + SETTLE or name in results:
                    skipped.append(dict(role=name, reason="settle" if name not in results else "done"))
                    continue
                time.sleep(max(0.0, seen_at + DWELL - time.monotonic()))
                wid = window()
                require(wid is not None, "Minecraft window not found")
                subprocess.run(["xdotool", "windowfocus", "--sync", wid], env=env, check=True, timeout=4)
                focus = subprocess.check_output(["xdotool", "getwindowfocus"], env=env, text=True).strip()
                title = subprocess.check_output(["xdotool", "getwindowname", wid], env=env, text=True).strip()
                require(focus == wid and "Minecraft" in title, "Window focus/title")
                a, b = private / ("%s-%d-a.png" % (name, len(retries))), private / ("%s-%d-b.png" % (name, len(retries)))
                grab(wid, a)
                time.sleep(PAIR)
                grab(wid, b)
                done_at = time.monotonic()
                time.sleep(0.4)  # let the server log catch up before judging the hold
                after = [e for e in events(text(), end) if e[0] in ("BEGIN", "DRIFT", "FAIL", "ABORT")]
                if after:
                    retries.append(dict(role=name, events=[e[:2] for e in after]))
                    require(len(retries) <= len(roles), "Too many invalidated captures")
                    continue
                target = out / (name + ".png")
                shutil.copyfile(a, target)
                ra, rb = rgb(a, env), rgb(b, env)
                require(len(ra) == len(rb) == F.WIDTH * F.HEIGHT * 3, "Raw frame size")
                row = F.role(name)
                info = dict(
                    file=target.name,
                    sha256=sha(target.read_bytes()),
                    pairSha256=sha(b.read_bytes()),
                    title=title,
                    secondsAfterReady=round(done_at - seen_at, 2),
                    pairMeanAbsDiff=mean_abs_diff(ra, rb),
                    frameMean=[round(sum(ra[c::3]) / (F.WIDTH * F.HEIGHT), 3) for c in range(3)],
                )
                if row["pose"] != "wide":
                    info["patches"] = [
                        dict(patch=s["patch"], meanSRGB8=patch_mean(ra, s["patch"]), pairMeanSRGB8=patch_mean(rb, s["patch"]))
                        for s in F.samples(row)
                    ]
                require(info["pairMeanAbsDiff"] < 12, "Unstable frame pair for " + name)
                results[name] = info
                order.append(name)
                print(name, json.dumps(info.get("patches", info["frameMean"])), flush=True)
        finally:
            wid = window() if p.poll() is None else None
            if wid:
                subprocess.run(["/tmp/aqualumen-wm-close", hex(int(wid))], check=True, env=env)
            try:
                p.wait(timeout=24)
            except subprocess.TimeoutExpired:
                p.terminate()
                p.wait(timeout=10)

    t = text()
    require(fatal(t) is None, str(fatal(t)))
    renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t).group(1).strip()
    require(lab.nvidia(renderer) and "All dimensions are saved" in t, "Clean NVIDIA shutdown not logged")
    require(tree(src) == source_manifest, "SOURCE WORLD CHANGED")
    for n, h in originals.items():
        require(sha((orig / n).read_bytes()) == h, "Original Lab file changed: " + n)
    (out / "complete.json").write_text(
        json.dumps(
            dict(
                renderer=renderer,
                glVersion=next((m.group(1).strip() for m in re.finditer(r"OpenGL Version: ([^\n]+)", t)), None),
                pack=pack.name,
                sha256=pack_sha,
                normalModFiles=mods,
                world=dict(name=lab.WORLD, worldId=lab.WORLD_ID, seed=SEED, sourceDigest=digest(source_manifest), sourceUnchanged=True),
                playerUuid=PLAYER_UUID,
                datapackDigest=pack_digest,
                scripts=script_hashes,
                referenceOptions={"COLORED_LIGHTS":True} if photon else {},
                originalLabFilesUnchanged=sorted(originals),
                width=F.WIDTH,
                height=F.HEIGHT,
                fovVertical=F.FOV,
                roles=roles,
                captureOrder=order,
                skippedHandshakes=skipped,
                invalidatedCaptures=retries,
                images=results,
                shaderFallback=False,
                note="display-referred 8-bit sRGB patch means from an ordinary Minecraft frame; not GPU readback",
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    if sys.argv[1:] == ["--dry-run"]:
        dry_run()
    else:
        main(sys.argv)
