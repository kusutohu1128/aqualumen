"""Native rain-on-stone fixture in a private, exact-UUID/seed copy of the Lab V2 world.

    python3 rain.py --dry-run                     # no lock, no world, no launch
    python3 rain.py build <run>                   # build the patio once, save it, keep the clone as snapshot
    python3 rain.py capture <pack.zip> <run>      # one scripted dry -> rain -> post-rain -> dry run
    python3 rain.py campaign                      # build if needed, 1.6.0 baseline, then wait for rc2

Ordinary client: the three normal mods only (Iris, Sodium, contact bridge 0.2.0), no recorder Mod.
The datapack is the only controller. Every scene re-verifies all 1800 reserved cells, the lamp cell, the
spectator pose, the absence of entities, the time of day and the server weather flag, then says READY;
it keeps re-verifying every 10 ticks (DRIFT). Time series (rain rise, drying) emit one MARK per interval
after the same verification, tagged -r/-c from the server's minecraft:weather_check predicate.
Per-cell sky access (can_see_sky), biome and raw light level (0..15) are reported by predicates.
Frames are x11grab captures of only the private client window. The source world must be unchanged.
"""

import fcntl
import gzip
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import anvil  # noqa: E402
import fixture as F  # noqa: E402

LOCK = "/tmp/aql-render21-1000.lock"
PLAYER_UUID = "00000000000040008000000000000521"
PLAYER_FILE = "00000000-0000-4000-8000-000000000521.dat"
SEED = 308060
NS = "aqr"
KIT = "RainEaves"
BIOME = "minecraft:ocean"
STATUS = HERE / "status.json"
BASE = ROOT / "dist/Aqualumen-1.6.0.zip"
BASE_SHA = "0b1843fd4172f80a2ffa3ce885974119b6c4b04b83a43f236bee96001be80a5e"
CANDIDATE = ROOT / "build/Aqualumen-1.7.0-rain-rc3.zip"  # parent: rc1 exceeds Iris 1.8.8's 16 custom images
CANDIDATE_PREFIX = "rc3"
SNAP_PREFIX = "aql-rain-fixture-build-"

CHECK = 40  # ticks after a hold scene starts before the verified READY
HOLD = 240  # ticks per held scene
WARMUP = 3000  # ticks between the first verification and the first scene (client loading took ~104 s once)
SETTLE = 20.0  # s after the client's live world render before a cycle may start
DWELL = 5.0  # s after READY before the first frame (lamp exposure adapts with a ~1.8 s constant)
GAP = 0.6  # s between frames of one hold
READY_RE = re.compile(r"\[Render thread/INFO\]: .*\[Aqualumen Physics\] .*bridge initialized")
EVENT_RE = re.compile(r"\[Server\] AQR_(READY|FAIL|DRIFT|BEGIN|ABORT|BUILT|MARK|INFO|DONE)_([a-z0-9-]+)_END")
ERROR_RE = re.compile(r"\[Render thread/ERROR\]|/ERROR\].*(aqr:|function|RainEaves)")

# (name, kind, weather, lamp, pose, frames | (interval ticks, marks))
SEQUENCE = [
    ("dry-a-on", "hold", "clear", "on", "a", 3),
    ("dry-b-on", "hold", "clear", "on", "b", 3),
    ("dry-a-off", "hold", "clear", "off", "a", 3),
    ("dry-b-off", "hold", "clear", "off", "b", 3),
    ("dry-wide-on", "hold", "clear", "on", "wide", 3),
    ("dry-a-ref", "hold", "clear", "on", "a", 3),
    ("rise", "series", "rain", "on", "a", (30, 40)),  # weather rain at its first tick; 60 s
    ("rain-a-on", "hold", "rain", "on", "a", 5),
    ("rain-b-on", "hold", "rain", "on", "b", 5),
    ("rain-a-off", "hold", "rain", "off", "a", 5),
    ("rain-b-off", "hold", "rain", "off", "b", 5),
    ("rain-wide-on", "hold", "rain", "on", "wide", 5),
    ("rain-a-repeat", "hold", "rain", "on", "a", 5),
    ("stop", "series", "clear", "on", "a", (40, 6)),  # weather clear at its first tick; 12 s
    ("post-b-on", "hold", "clear", "on", "b", 4),
    ("post-a-off", "hold", "clear", "off", "a", 4),
    ("post-a-on", "hold", "clear", "on", "a", 4),
    ("post-wide-on", "hold", "clear", "on", "wide", 4),
    ("drying", "series", "clear", "on", "a", (60, 45)),  # 135 s
    ("final-a-on", "hold", "clear", "on", "a", 3),
    ("final-b-on", "hold", "clear", "on", "b", 3),
    ("final-a-off", "hold", "clear", "off", "a", 3),
    ("final-b-off", "hold", "clear", "off", "b", 3),
    ("final-wide-on", "hold", "clear", "on", "wide", 3),
]
NAMES = [s[0] for s in SEQUENCE]
END_LAMP = SEQUENCE[-1][3]


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def status(**fields):
    cur = json.loads(STATUS.read_text()) if STATUS.exists() else {}
    cur.update(fields, updated=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, STATUS)


def timeline():
    """Scene start times in seconds after the first scene (server ticks / 20)."""
    t, out = 0, []
    for name, kind, *_rest, n in SEQUENCE:
        out.append((name, t / 20))
        t += HOLD if kind == "hold" else n[0] * n[1]
    return out, t / 20


# ---------------------------------------------------------------- datapack (pure)


def w(p):
    return " ".join(str(v) for v in F.world(p))


def fill(b, block):
    lo, hi = b
    return "fill %s %s %s" % (w(lo), w(tuple(v - 1 for v in hi)), block)


def wrap(a):
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def pose_selector(pose):
    yaw, pitch = pose["yaw"], pose["pitch"]
    return "@a[name=%s,distance=..0.01,gamemode=spectator,x_rotation=%s..%s,y_rotation=%s..%s]" % (
        F.PLAYER, F.fmt(pitch - 0.05), F.fmt(pitch + 0.05), F.fmt(wrap(yaw - 0.05)), F.fmt(wrap(yaw + 0.05)))


def tp(pose):
    return "tp %s %s %s %s" % (F.PLAYER, " ".join(F.fmt(v) for v in F.feet(pose)), F.fmt(pose["yaw"]), F.fmt(pose["pitch"]))


def count(cell, block):
    return "execute if block %s %s run scoreboard players add #n %s 1" % (w(cell), block, NS)


def probe_cell(s):
    """Air cell whose light/sky/biome describe the receiver point (cell in front of the face)."""
    x, y, z = s["point"]
    if s["block"] == F.WALL:
        return (int(x), int(y), int(z))
    return (int(x), int(y), int(z))


def predicates():
    out = {
        "raining": {"condition": "minecraft:weather_check", "raining": True},
        "thundering": {"condition": "minecraft:weather_check", "thundering": True},
        "dusk": {"condition": "minecraft:time_check", "value": F.TIME, "period": 24000},
        "sky": {"condition": "minecraft:location_check", "predicate": {"can_see_sky": True}},
        "biome": {"condition": "minecraft:location_check", "predicate": {"biomes": BIOME}},
    }
    for k in range(16):
        out["light%d" % k] = {"condition": "minecraft:location_check", "predicate": {"light": {"light": {"min": k, "max": k}}}}
    return out


def info_lines(tag):
    """Server-side exposure/access: sky visibility, biome and raw light (max(sky - darkening, block))."""
    lines = ["execute if predicate %s:raining run say AQR_INFO_%s-rain-1_END" % (NS, tag),
             "execute unless predicate %s:raining run say AQR_INFO_%s-rain-0_END" % (NS, tag),
             "execute if predicate %s:thundering run say AQR_INFO_%s-thunder-1_END" % (NS, tag)]
    for i, s in enumerate(F.SAMPLES):
        at = "execute positioned %s" % w(probe_cell(s))
        lines.append("%s if predicate %s:sky run say AQR_INFO_%s-sky-s%d-1_END" % (at, NS, tag, i))
        lines.append("%s unless predicate %s:sky run say AQR_INFO_%s-sky-s%d-0_END" % (at, NS, tag, i))
        lines.append("%s unless predicate %s:biome run say AQR_INFO_%s-biome-s%d-0_END" % (at, NS, tag, i))
        for k in range(16):
            lines.append("%s if predicate %s:light%d run say AQR_INFO_%s-light-s%d-%d_END" % (at, NS, k, tag, i, k))
    return lines


def datapack(mode):
    assert mode in ("build", "capture")
    lo_w, hi_w = F.world(F.LO), F.world(F.HI)
    files = {
        "pack.mcmeta": json.dumps({"pack": {"pack_format": 48, "description": "Private Aqualumen rain-eave fixture"}}),
        "data/minecraft/tags/function/tick.json": json.dumps({"values": [NS + ":tick"]}),
    }
    for k, v in predicates().items():
        files["data/%s/predicate/%s.json" % (NS, k)] = json.dumps(v)
    fn = {}
    tag = "aqr_" + mode  # per mode: the build's tag is saved in the snapshot's player data
    fn["tick"] = ["execute as @a[name=%s,tag=!%s] run function %s:start" % (F.PLAYER, tag, NS)]
    fn["start"] = [
        "tag @s add " + tag,
        "gamerule doDaylightCycle false", "gamerule doWeatherCycle false", "gamerule doMobSpawning false",
        "gamerule randomTickSpeed 0", "gamerule doFireTick false", "gamerule sendCommandFeedback false",
        "gamerule commandBlockOutput false", "gamerule announceAdvancements false", "difficulty peaceful",
        "weather clear", "time set %d" % F.TIME, "gamemode spectator @s",
        "scoreboard objectives add %s dummy" % NS,
        "scoreboard players set #attempt %s 0" % NS, "scoreboard players set #built %s 0" % NS,
        "forceload add %d %d %d %d" % (lo_w[0], lo_w[2], hi_w[0], hi_w[2]),
        tp(F.POSES["a"]),
        "schedule function %s:setup 20t replace" % NS,
    ]
    corners = [(x, lo_w[1], z) for x in (lo_w[0], hi_w[0]) for z in (lo_w[2], hi_w[2])]
    loaded = " ".join("if loaded %d %d %d" % c for c in corners)
    after = "reserve" if mode == "build" else "vstart"
    fn["setup"] = [
        "scoreboard players add #attempt %s 1" % NS,
        "scoreboard players set #loaded %s 0" % NS,
        "execute %s run scoreboard players set #loaded %s 1" % (loaded, NS),
        "execute if score #loaded %s matches 0 if score #attempt %s matches ..60 run schedule function %s:setup 20t replace" % (NS, NS, NS),
        "execute if score #loaded %s matches 0 if score #attempt %s matches 61.. run say AQR_ABORT_unloaded_END" % (NS, NS),
        "execute if score #loaded %s matches 1 if score #built %s matches 0 run function %s:%s" % (NS, NS, NS, after),
    ]
    room = "positioned %s unless entity @e[type=!minecraft:player,dx=%d,dy=%d,dz=%d]" % (
        w(F.LO), F.HI[0] - F.LO[0], F.HI[1] - F.LO[1], F.HI[2] - F.LO[2])
    static = F.cells("on")
    fn["vstatic"] = [count(c, b) for c, b in sorted(static.items()) if c != F.LAMP_CELL]
    for lamp in ("on", "off"):
        fn["vlamp" + lamp] = [count(F.LAMP_CELL, F.LAMP[lamp])]

    def verify(lamp, pose, weather=None):
        cond = "execute if score #n %s matches %d %s if predicate %s:dusk" % (NS, F.CELLS, room, NS)
        if weather == "rain":
            cond += " if predicate %s:raining" % NS
        elif weather == "clear":
            cond += " unless predicate %s:raining" % NS
        if pose:
            cond += " positioned %s if entity %s" % (" ".join(F.fmt(v) for v in F.feet(F.POSES[pose])), pose_selector(F.POSES[pose]))
        return ["scoreboard players set #n %s 0" % NS, "scoreboard players set #ok %s 0" % NS,
                "function %s:vstatic" % NS, "function %s:vlamp%s" % (NS, lamp),
                cond + " run scoreboard players set #ok %s 1" % NS]

    if mode == "build":
        reserve = ["scoreboard players set #n %s 0" % NS] + [count(c, F.AIR) for c in sorted(static)]
        reserve += ["execute if score #n %s matches %d run function %s:build" % (NS, F.CELLS, NS),
                    "execute unless score #n %s matches %d run say AQR_ABORT_reserved_END" % (NS, F.CELLS)]
        fn["reserve"] = reserve
        fn["build"] = (["scoreboard players set #built %s 1" % NS] + [fill(b, blk) for b, blk in F.SHELL]
                       + ["setblock %s %s" % (w(F.LAMP_CELL), F.LANTERN), "schedule function %s:built 40t replace" % NS])
        fn["vb"] = verify("on", "a", "clear")
        fn["built"] = (["function %s:vb" % NS] + info_lines("built")
                       + ["execute if score #ok %s matches 1 run say AQR_BUILT_patio_END" % NS,
                          "execute if score #ok %s matches 0 run say AQR_FAIL_built_END" % NS,
                          "schedule function %s:hb 20t replace" % NS])
        fn["hb"] = ["function %s:vb" % NS, "execute if score #ok %s matches 0 run say AQR_DRIFT_built_END" % NS,
                    "schedule function %s:hb 20t replace" % NS]
    else:
        # The build's hold check is still scheduled in the saved snapshot: make it a no-op here.
        fn["hb"] = ["# build-time hold check disabled in capture copies"]
        # The saved snapshot ends with the lamp `on` (build) - verify it before touching anything.
        fn["vs"] = verify("on", None, None)
        fn["vstart"] = (["scoreboard players set #built %s 1" % NS, "function %s:vs" % NS]
                        + ["execute if score #ok %s matches 1 run say AQR_INFO_static-ok_END" % NS,
                           "execute if score #ok %s matches 0 run say AQR_ABORT_static_END" % NS,
                           "execute if score #ok %s matches 1 run schedule function %s:s0 %dt replace" % (NS, NS, WARMUP)])
        n = len(SEQUENCE)
        for i, (name, kind, weather, lamp, pose, arg) in enumerate(SEQUENCE):
            scene = ["schedule clear %s:h%d" % (NS, j) for j in range(n)]
            scene += ["schedule clear %s:m%d" % (NS, j) for j in range(n) if SEQUENCE[j][1] == "series"]
            scene += ["say AQR_BEGIN_%s_END" % name, "time set %d" % F.TIME,
                      "weather rain 1000000" if weather == "rain" else "weather clear 1000000",
                      "setblock %s %s" % (w(F.LAMP_CELL), F.LAMP[lamp]), tp(F.POSES[pose])]
            nxt = "s%d" % (i + 1) if i + 1 < n else "done"
            fn["v%d" % i] = verify(lamp, pose, weather if kind == "hold" else None)
            if kind == "hold":
                scene += ["schedule function %s:c%d %dt replace" % (NS, i, CHECK),
                          "schedule function %s:%s %dt replace" % (NS, nxt, HOLD)]
                fn["c%d" % i] = (["function %s:v%d" % (NS, i)] + info_lines("h%d" % i)
                                 + ["execute if score #ok %s matches 1 run say AQR_READY_%s_END" % (NS, name),
                                    "execute if score #ok %s matches 0 run say AQR_FAIL_%s_END" % (NS, name),
                                    "schedule function %s:h%d 10t replace" % (NS, i)])
                fn["h%d" % i] = ["function %s:v%d" % (NS, i),
                                 "execute if score #ok %s matches 0 run say AQR_DRIFT_%s_END" % (NS, name),
                                 "schedule function %s:h%d 10t replace" % (NS, i)]
            else:
                interval, marks = arg
                scene += ["scoreboard players set #k %s 0" % NS, "schedule function %s:m%d %dt replace" % (NS, i, interval)]
                fn["m%d" % i] = ["function %s:v%d" % (NS, i), "scoreboard players add #k %s 1" % NS,
                                 "execute if score #ok %s matches 1 if predicate %s:raining run say AQR_MARK_%s-r_END" % (NS, NS, name),
                                 "execute if score #ok %s matches 1 unless predicate %s:raining run say AQR_MARK_%s-c_END" % (NS, NS, name),
                                 "execute if score #ok %s matches 0 run say AQR_FAIL_%s_END" % (NS, name),
                                 "execute if score #k %s matches ..%d run schedule function %s:m%d %dt replace" % (NS, marks - 1, NS, i, interval),
                                 "execute if score #k %s matches %d.. run function %s:%s" % (NS, marks, NS, nxt)]
            fn["s%d" % i] = scene
        # The cycle repeats (the final scenes are already >3 min dry), so a slow client can join the next one.
        fn["done"] = (["schedule clear %s:h%d" % (NS, j) for j in range(n)] + ["function %s:v%d" % (NS, n - 1)]
                      + info_lines("end")
                      + ["execute if score #ok %s matches 1 run say AQR_DONE_sequence_END" % NS,
                         "execute if score #ok %s matches 0 run say AQR_FAIL_done_END" % NS,
                         "schedule function %s:s0 20t replace" % NS])
    for k, lines in fn.items():
        files["data/%s/function/%s.mcfunction" % (NS, k)] = "\n".join(lines) + "\n"
    return files


def check_datapack(files, mode):
    lo_w, hi_w = F.world(F.LO), F.world(F.HI)
    coord = re.compile(r"(?:block|fill|setblock|loaded|positioned) (-?\d+) (-?\d+) (-?\d+)")
    for path, text in files.items():
        for line in text.splitlines():
            for m in coord.finditer(line):
                x, y, z = map(int, m.groups())
                require(lo_w[0] <= x <= hi_w[0] and lo_w[1] <= y <= hi_w[1] and lo_w[2] <= z <= hi_w[2],
                        "outside the reserved volume: " + line)
            # Only weather rain/clear, time set and our own blocks; nothing else may change the world.
            if not path.endswith(".mcfunction") or line.startswith("#"):
                continue
            first = line.split(" ", 1)[0]
            require(first in ("execute", "scoreboard", "schedule", "say", "function", "tag", "gamerule", "difficulty",
                              "weather", "time", "gamemode", "forceload", "tp", "fill", "setblock"), line)
            if first in ("fill", "setblock"):
                name = path.rsplit("/", 1)[-1]
                require((mode == "build" and name == "build.mcfunction") or re.fullmatch(r"s\d+\.mcfunction", name), path)
    fdir = "data/%s/function/" % NS
    require(sum(l.startswith("execute if block") for l in files[fdir + "vstatic.mcfunction"].splitlines()) == F.CELLS - 1, "vstatic")
    for name in files:
        if name.startswith(fdir + "c") or name.startswith(fdir + "m"):
            require("function %s:v" % NS in files[name], name)


def simulate(files, mode):
    """Replay build/scene fill/setblock/tp/weather on an all-air grid and compare with the fixture."""
    fdir = "data/%s/function/" % NS
    grid = {F.world(c): F.AIR for c in F.cells("on")}
    fill_re = re.compile(r"^fill (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (\S+)$")
    set_re = re.compile(r"^setblock (-?\d+) (-?\d+) (-?\d+) (\S+)$")
    tp_re = re.compile(r"^tp %s (\S+) (\S+) (\S+) (\S+) (\S+)$" % F.PLAYER)
    count_re = re.compile(r"^execute if block (-?\d+) (-?\d+) (-?\d+) (\S+) run scoreboard")
    state = dict(player=None, weather=None)

    def run(name):
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
                state["player"] = tuple(map(float, m.groups()))
            elif line.startswith("weather "):
                state["weather"] = line.split()[1]

    def counted(names):
        lines = []
        for n in names:
            lines += files[fdir + n + ".mcfunction"].splitlines()
        hits = [m for m in map(count_re.match, lines) if m]
        require(len(hits) == F.CELLS and len({m.groups()[:3] for m in hits}) == F.CELLS, "verification cell count")
        return all(grid[tuple(map(int, m.groups()[:3]))] == m.group(4) for m in hits)

    if mode == "build":
        run("build")
        require(grid == {F.world(c): b for c, b in F.cells("on").items()}, "build differs from fixture")
        require(counted(["vstatic", "vlampon"]), "build verification")
        return
    grid.update({F.world(c): b for c, b in F.cells("on").items()})
    require(counted(["vstatic", "vlampon"]), "snapshot verification")
    for i, (name, kind, weather, lamp, pose, arg) in enumerate(SEQUENCE):
        run("s%d" % i)
        require(grid == {F.world(c): b for c, b in F.cells(lamp).items()}, name + ": cells")
        require(counted(["vstatic", "vlamp" + lamp]), name + ": verification")
        require(not counted(["vstatic", "vlamp" + ("off" if lamp == "on" else "on")]), name + ": lamp check is blind")
        p = F.POSES[pose]
        require(max(abs(a - b) for a, b in zip(state["player"][:3], F.feet(p))) < 1e-9
                and (state["player"][3], state["player"][4]) == (p["yaw"], p["pitch"]), name + ": pose")
        require(state["weather"] == weather, name + ": weather")
        v = files[fdir + "v%d.mcfunction" % i]
        require(("vlamp" + lamp) in v and pose_selector(p) in v, name + ": verify target")


# ---------------------------------------------------------------- image helpers


def png_size(path):
    import struct
    head = path.read_bytes()[:24]
    require(head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR", "Not a PNG: " + path.name)
    return struct.unpack(">II", head[16:24])


def rgb(path):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:"],
                          check=True, capture_output=True, timeout=10).stdout


def patch_mean(raw, rect):
    x0, y0, x1, y1 = rect
    acc = [0, 0, 0]
    for y in range(y0, y1):
        row = raw[(y * F.WIDTH + x0) * 3:(y * F.WIDTH + x1) * 3]
        for c in range(3):
            acc[c] += sum(row[c::3])
    n = (x1 - x0) * (y1 - y0)
    return [round(a / n, 3) for a in acc]


def measure(raw, pose):
    return {s["name"]: patch_mean(raw, s["patch"]) for s in F.samples(pose) if s["valid"]}


# ---------------------------------------------------------------- world helpers (from the indirect runner)


def tree(folder, skip=("session.lock",)):
    out = {}
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder).as_posix()
        require(not path.is_symlink(), "Symlink in world tree: " + rel)
        if path.is_file() and rel not in skip:
            out[rel] = sha(path.read_bytes())
    return out


def copy_world(src, dst, skip=lambda rel: False):
    manifest = {}
    dst.mkdir()
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src).as_posix()
        require(not path.is_symlink(), "Symlink in world tree: " + rel)
        if rel == "session.lock" or skip(rel):
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


def events(text, start=0):
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
        return "Error line: " + text[text.rfind("\n", 0, m.start()) + 1:text.find("\n", m.start())][:300]
    for kind, role, _ in events(text):
        if kind == "ABORT":
            return "Fixture aborted: " + role
        if kind in ("FAIL", "DRIFT"):
            return "Fixture verification %s: %s" % (kind.lower(), role)
    return None


def parse_info(names):
    """AQR_INFO_<tag>-<kind>-s<i>-<v> -> {tag: {kind: {sample: v}}}"""
    out = {}
    for n in names:
        m = re.fullmatch(r"([a-z0-9]+)-(sky|biome|light)-s(\d+)-(\d+)", n)
        if m:
            tag, kind, i, v = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
            out.setdefault(tag, {}).setdefault(kind, {})[F.SAMPLES[i]["name"]] = v
            continue
        m = re.fullmatch(r"([a-z0-9]+)-(rain|thunder)-(\d)", n)
        if m:
            out.setdefault(m.group(1), {})[m.group(2)] = int(m.group(3))
    return out


def saved_cells(world_dir, lamp):
    """Read back every reserved cell and the receiver cells' saved light from the clone after exit."""
    wr = anvil.World(world_dir)
    want = F.cells(lamp)
    bad = []
    for c, b in sorted(want.items()):
        got = wr.block(*F.world(c))
        norm = got.replace("[axis=y]", "[axis=y]") if got else got
        if norm != b:
            bad.append(dict(cell=list(c), want=b, got=got))
    light = {}
    for s in F.SAMPLES:
        p = F.world(probe_cell(s))
        light[s["name"]] = dict(cell=list(p), sky=wr.light(*p, "SkyLight"), block=wr.light(*p, "BlockLight"),
                                biome=wr.biome(*p), motionBlocking=wr.height(p[0], p[2]))
    return bad, light


# ---------------------------------------------------------------- dry run


def dry_run():
    t0 = time.monotonic()
    rep = F.selftest()
    for mode in ("build", "capture"):
        files = datapack(mode)
        check_datapack(files, mode)
        simulate(files, mode)
        target = Path(tempfile.mkdtemp(prefix="aql-rain-fixture-dry-%s-" % mode))
        for rel, text in files.items():
            p = target / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        print(mode, "datapack ok:", target, "| functions", sum(1 for k in files if k.endswith(".mcfunction")),
              "| longest", max(len(t.splitlines()) for t in files.values()), "lines")
    for n in ("a-on", "built-sky-s3-1", "h7-light-s0-12", "end-rain-0"):
        require(EVENT_RE.search("[Server] AQR_INFO_%s_END" % n), n)
    require(parse_info(["h7-light-s0-12", "h7-rain-1", "built-sky-s3-0"]) ==
            {"h7": {"light": {F.SAMPLES[0]["name"]: 12}, "rain": 1}, "built": {"sky": {F.SAMPLES[3]["name"]: 0}}}, "info parse")
    log = ("[Server thread/INFO]: [Not Secure] [Server] AQR_READY_dry-a-on_END\n"
           "[Render thread/INFO]: [STDOUT]: [Aqualumen Physics] 0.2.0 contact bridge initialized (512)\n"
           "[Server thread/INFO]: [Not Secure] [Server] AQR_MARK_rise-r_END\n")
    require(READY_RE.search(log) and fatal(log) is None, "log parse")
    require(fatal(log + "[Server] AQR_DRIFT_rain-a-on_END\n") == "Fixture verification drift: rain-a-on", "drift")
    plan_t, total = timeline()
    print("timeline:", ", ".join("%s@%.0fs" % r for r in plan_t), "| total %.0f s + warmup %.0f s" % (total, WARMUP / 20))
    for name in F.POSES:
        print(name, json.dumps(rep[name]["pose"]))
    print("dry run ok %.1fs" % (time.monotonic() - t0))


# ---------------------------------------------------------------- launch


def lab_modules():
    sys.path.insert(0, str(ROOT / "tools"))
    import ground_shadow_lab as g
    return g.lab, g.GAME.resolve()


def prepare_game(prefix, pack, lab, orig):
    parent = Path(tempfile.mkdtemp(prefix=prefix, dir="/tmp")).resolve()
    require(parent.parent == Path("/tmp") and parent.name.startswith("aql-rain-fixture-"), "clone path")
    game = parent / "minecraft"
    game.mkdir()
    for n in ["shaderpacks", "mods", "config", "saves"]:
        (game / n).mkdir()
    mods = {n: sha((orig / "mods" / n).read_bytes()) for n in sorted(lab.NORMAL_MODS)}
    for n in sorted(lab.NORMAL_MODS):
        shutil.copy(orig / "mods" / n, game / "mods")
        require(sha((game / "mods" / n).read_bytes()) == mods[n], "Mod copy differs")
    shutil.copy(pack, game / "shaderpacks")
    for n in ["sodium-options.json", "iris.properties"]:
        if (orig / "config" / n).exists():
            shutil.copy(orig / "config" / n, game / "config")
    iris = game / "config/iris.properties"
    iris.write_bytes(lab.replace_values(iris.read_bytes(), {"shaderPack": pack.name}, "="))
    require(lab.pairs(iris.read_bytes()).get("enableShaders", "true") == "true", "Shaders disabled in config")
    options = dict(lab.OPTIONS, maxFps="120", overrideWidth=str(F.WIDTH), overrideHeight=str(F.HEIGHT),
                   pauseOnLostFocus="false", chatVisibility="2", fov=F.fmt((F.FOV - 70) / 40),
                   fovEffectScale="0.0", bobView="false")
    (game / "options.txt").write_bytes(lab.replace_values((orig / "options.txt").read_bytes(), options, ":"))
    return parent, game, mods, options


def java_args(game, orig, runtime):
    return [runtime["java"], "-Xms512m", "-Xmx2600m", "-XX:ActiveProcessorCount=4",
            "-Dorg.lwjgl.openal.libname=libopenal.so.1", "-cp", ":".join(runtime["cp"]),
            "net.fabricmc.loader.impl.launch.knot.KnotClient", "--username", F.PLAYER, "--version", "1.21.1",
            "--gameDir", str(game), "--assetsDir", str(orig.parents[2] / "assets"), "--assetIndex", "17",
            "--uuid", PLAYER_UUID, "--accessToken", "0", "--userType", "legacy",
            "--width", str(F.WIDTH), "--height", str(F.HEIGHT), "--quickPlaySingleplayer", "AqualumenNaturalV2"]


def env_for(parent):
    env = dict(os.environ, DISPLAY=":1", XDG_RUNTIME_DIR="/run/user/1000",
               DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus", __GLX_VENDOR_LIBRARY_NAME="nvidia",
               ALSOFT_DRIVERS="null", XDG_CACHE_HOME=str(parent / "cache"))
    for k in ["JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "GALLIUM_DRIVER", "LIBGL_KOPPER_DRI2", "VK_DRIVER_FILES"]:
        env.pop(k, None)
    return env


class Client:
    def __init__(self, args, game, env, log):
        self.env, self.log = env, log
        self.stream = log.open("xb")
        self.p = subprocess.Popen(args, stdout=self.stream, stderr=self.stream, env=env, cwd=game)

    def text(self):
        return self.log.read_text(errors="replace")

    def window(self):
        r = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid", str(self.p.pid), "--name", "Minecraft"],
                           env=self.env, text=True, capture_output=True)
        return r.stdout.strip() if r.returncode == 0 and len(r.stdout.split()) == 1 else None

    def focus(self):
        wid = self.window()
        require(wid is not None, "Minecraft window not found")
        subprocess.run(["xdotool", "windowfocus", "--sync", wid], env=self.env, check=True, timeout=4)
        focus = subprocess.check_output(["xdotool", "getwindowfocus"], env=self.env, text=True).strip()
        title = subprocess.check_output(["xdotool", "getwindowname", wid], env=self.env, text=True).strip()
        require(focus == wid and "Minecraft" in title, "Window focus/title")
        return wid, title

    def grab(self, wid, target):
        subprocess.run(["ffmpeg", "-v", "error", "-n", "-f", "x11grab", "-window_id", wid, "-i", self.env["DISPLAY"],
                        "-frames:v", "1", "-threads", "1", str(target)], env=self.env, check=True, timeout=6)
        require(png_size(target) == (F.WIDTH, F.HEIGHT), "Frame size")

    def wait_ready(self, pack_name, lab, timeout=300):
        deadline = time.monotonic() + timeout
        while not (ready := READY_RE.search(t := self.text())):
            require(fatal(t) is None, str(fatal(t)))
            require(self.p.poll() is None and time.monotonic() < deadline, "Client never reached a live world render")
            time.sleep(0.3)
        renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t)
        require(renderer and lab.nvidia(renderer.group(1)), "Not the NVIDIA renderer")
        require("Using shaderpack: " + pack_name in t, "Iris did not select the pack")
        return ready.end()

    def close(self):
        try:
            wid = self.window() if self.p.poll() is None else None
            if wid:
                subprocess.run(["/tmp/aqualumen-wm-close", hex(int(wid))], check=True, env=self.env)
            try:
                self.p.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.p.terminate()
                self.p.wait(timeout=10)
        finally:
            self.stream.close()


def guard_source(lab, orig):
    src = orig / "saves" / lab.WORLD
    require(src.is_dir() and not src.is_symlink() and src.resolve().parent == orig / "saves", "Source world path")
    lab.shared.world_marker()
    return src


def check_clone(world, lab, src_manifest=None):
    marker = lab.pairs((world / "aqualumen-world.properties").read_bytes())
    require(marker.get("world_id") == lab.WORLD_ID and marker.get("seed") == str(SEED), "Clone UUID/seed marker")
    lv = anvil.level(world)
    require(lv["Data"]["WorldGenSettings"]["seed"] == SEED, "level.dat seed differs")
    return marker


def originals_of(orig):
    return {n: sha((orig / n).read_bytes()) for n in ("options.txt", "config/iris.properties", "config/sodium-options.json")
            if (orig / n).is_file()}


# ---------------------------------------------------------------- build


def build(run):
    require(os.getuid() == 1000, "uid")
    require(re.fullmatch(r"build-r\d+", run) is not None, "build run name")
    out = HERE / run
    require(not out.exists(), "run dir exists")
    files = datapack("build")
    check_datapack(files, "build")
    simulate(files, "build")
    F.selftest()
    pack = BASE
    require(sha(pack.read_bytes()) == BASE_SHA, "1.6.0 hash")
    lock = open(LOCK, "a+b")
    fcntl.flock(lock, fcntl.LOCK_EX)
    lab, orig = lab_modules()
    runtime = json.loads((ROOT / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
    src = guard_source(lab, orig)
    originals = originals_of(orig)
    out.mkdir()
    parent, game, mods, options = prepare_game(SNAP_PREFIX, pack, lab, orig)
    (out / "private-game.txt").write_text(str(game) + "\n")
    with (src / "session.lock").open("r+b") as f:
        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = copy_world(src, game / "saves" / lab.WORLD)
    world = game / "saves" / lab.WORLD
    require(tree(world) == manifest, "Clone differs from source")
    check_clone(world, lab)
    require(not (world / "playerdata" / PLAYER_FILE).exists() and not (world / "datapacks" / KIT).exists(), "fresh clone")
    for rel, text in files.items():
        p = world / "datapacks" / KIT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    (out / "datapack-digest.txt").write_text(digest({k: sha(v.encode()) for k, v in files.items()}) + "\n")
    env = env_for(parent)
    c = Client(java_args(game, orig, runtime), game, env, out / "client.log")
    infos = []
    try:
        cursor = c.wait_ready(pack.name, lab)
        deadline = time.monotonic() + 180
        built = None
        while built is None:
            t = c.text()
            require(fatal(t) is None, str(fatal(t)))
            require(c.p.poll() is None and time.monotonic() < deadline, "patio never verified")
            for kind, name, end in events(t):
                if kind == "INFO":
                    infos.append(name)
                if kind == "BUILT":
                    built = end
            time.sleep(0.3)
        status(phase="build: patio verified, letting light settle before save")
        time.sleep(25)  # skylight/blocklight propagation and a clean autosave-independent exit
        wid, title = c.focus()
        c.grab(wid, out / "built-a.png")
        t = c.text()
        require(fatal(t) is None, str(fatal(t)))
    finally:
        c.close()
    t = c.text()
    renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t).group(1).strip()
    require(lab.nvidia(renderer) and "All dimensions are saved" in t, "Clean NVIDIA shutdown not logged")
    require(tree(src) == manifest, "SOURCE WORLD CHANGED")
    for n, h in originals.items():
        require(sha((orig / n).read_bytes()) == h, "Original Lab file changed: " + n)
    bad, light = saved_cells(world, "on")
    require(not bad, "saved patio differs: %s" % bad[:3])
    info = parse_info(infos).get("built", {})
    for s in F.SAMPLES:
        if s["block"] != F.WALL:
            require(info["sky"][s["name"]] == int(s["exposed"]), "can_see_sky disagrees with the eave: " + s["name"])
    require(not info.get("biome"), "non-ocean biome at a receiver")
    # Freeze the saved geometry: the snapshot is read-only from here on.
    snap = tree(world)
    for p in sorted(world.rglob("*"), reverse=True):
        if p.is_file():
            p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    (out / "complete.json").write_text(json.dumps(dict(
        renderer=renderer, pack=pack.name, sha256=BASE_SHA, normalModFiles=mods, options=options,
        world=dict(name=lab.WORLD, worldId=lab.WORLD_ID, seed=SEED, sourceDigest=digest(manifest), sourceUnchanged=True),
        snapshot=dict(path=str(world), digest=digest(snap), files=len(snap), readOnly=True),
        savedCellsExact=F.CELLS, savedReceiverLight=light, serverAccess=info, playerUuid=PLAYER_UUID,
        datapackDigest=(out / "datapack-digest.txt").read_text().strip(), originalLabFilesUnchanged=sorted(originals),
        scripts={n: sha((HERE / n).read_bytes()) for n in ("rain.py", "fixture.py", "anvil.py")},
        origin=F.ORIGIN, reserved=dict(local=[F.LO, F.HI], world=[F.world(F.LO), F.world(F.HI)], cells=F.CELLS)),
        indent=2))
    return out


def snapshot():
    for d in sorted(HERE.glob("build-r*")):
        f = d / "complete.json"
        if f.is_file():
            j = json.loads(f.read_text())
            return Path(j["snapshot"]["path"]), j
    return None, None


# ---------------------------------------------------------------- capture


def capture(pack, run):
    require(os.getuid() == 1000, "uid")
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}-r\d+", run) is not None, "run name")
    pack = Path(pack)
    require(pack.is_file() and not pack.is_symlink() and pack.suffix == ".zip", "Pack must be a regular .zip")
    pack = pack.resolve()
    pack_sha = sha(pack.read_bytes())
    out = HERE / run
    require(not out.exists(), "run dir exists")
    snap, receipt = snapshot()
    require(snap is not None and snap.is_dir(), "no saved patio snapshot (run build first)")
    require(digest(tree(snap)) == receipt["snapshot"]["digest"], "snapshot changed")
    files = datapack("capture")
    check_datapack(files, "capture")
    simulate(files, "capture")
    F.selftest()
    with ZipFile(pack) as z:
        props = z.read("shaders/shaders.properties").decode("utf-8", "replace")
        halflife = {k: v for k, v in re.findall(r"^\s*(wetnessHalfLife|drynessHalfLife)\s*=\s*(\S+)", props, re.M)}
        # Iris also reads `const float wetnessHalflife/drynessHalflife` directives from shader sources
        for n in z.namelist():
            if n.endswith((".glsl", ".fsh", ".vsh", ".csh", ".gsh")):
                for k, v in re.findall(r"const\s+float\s+(wetnessHalflife|drynessHalflife)\s*=\s*([0-9.]+)",
                                       z.read(n).decode("utf-8", "replace")):
                    halflife[k + "@" + n] = v
    halflife = halflife or {"note": "none declared: Iris defaults"}
    lock = open(LOCK, "a+b")
    fcntl.flock(lock, fcntl.LOCK_EX)
    lab, orig = lab_modules()
    runtime = json.loads((ROOT / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
    src = guard_source(lab, orig)
    src_manifest = tree(src)
    originals = originals_of(orig)
    out.mkdir()
    (out / "frames").mkdir()
    parent, game, mods, options = prepare_game("aql-rain-fixture-%s-" % run, pack, lab, orig)
    (out / "private-game.txt").write_text(str(game) + "\n")
    world = game / "saves" / lab.WORLD
    manifest = copy_world(snap, world, skip=lambda rel: rel.startswith("datapacks/%s/" % KIT) or rel == "datapacks/" + KIT)
    for p in world.rglob("*"):
        if p.is_file():
            p.chmod(p.stat().st_mode | stat.S_IWUSR)
    check_clone(world, lab)
    for rel, text in files.items():
        p = world / "datapacks" / KIT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    plan = dict(pack=pack.name, packSha256=pack_sha, declaredHalfLives=halflife, options=options,
                snapshot=dict(path=str(snap), digest=receipt["snapshot"]["digest"], buildRun=snap and receipt.get("datapackDigest")),
                world=dict(name=lab.WORLD, worldId=lab.WORLD_ID, seed=SEED, sourceDigest=digest(src_manifest)),
                datapackDigest=digest({k: sha(v.encode()) for k, v in files.items()}), playerUuid=PLAYER_UUID,
                sequence=[dict(name=n, kind=k, weather=wx, lamp=l, pose=p, frames=a if k == "hold" else None,
                               series=dict(intervalTicks=a[0], marks=a[1]) if k == "series" else None)
                          for n, k, wx, l, p, a in SEQUENCE],
                timelineSeconds=dict(timeline()[0]), timing=dict(checkTicks=CHECK, holdTicks=HOLD, warmupTicks=WARMUP,
                                                                  dwellSeconds=DWELL, gapSeconds=GAP),
                poses={n: F.pose_record(n) for n in F.POSES},
                samples={n: F.samples(n) for n in F.POSES}, lamp=dict(cell=F.LAMP_CELL, centre=F.LAMP_CENTRE, block=F.LANTERN),
                scripts={n: sha((HERE / n).read_bytes()) for n in ("rain.py", "fixture.py", "anvil.py")})
    (out / "plan.json").write_text(json.dumps(plan, indent=2))
    env = env_for(parent)
    c = Client(java_args(game, orig, runtime), game, env, out / "client.log")
    holds, series, infos, skipped = {}, {}, {}, []
    begins = {}
    t_ready = None
    try:
        cursor = c.wait_ready(pack.name, lab)
        t_ready = time.monotonic()
        deadline = t_ready + WARMUP / 20 + 2 * timeline()[1] + 180
        done = False
        info_buf = []
        armed = None  # monotonic time of the first `dry-a-on` BEGIN seen >= SETTLE s after the live render
        cycles_skipped = 0
        while not done:
            t = c.text()
            require(fatal(t) is None, str(fatal(t)))
            require(c.p.poll() is None and time.monotonic() < deadline, "sequence not finished")
            new = events(t, cursor)
            if not new:
                time.sleep(0.1)
                continue
            # MARKs: only the newest pending mark of a series is grabbed; older ones are recorded as skipped.
            kind, name, end = new[0]
            cursor = end
            now = time.monotonic()
            if armed is None:
                if kind == "BEGIN" and name == NAMES[0]:
                    if now - t_ready >= SETTLE:
                        armed = now
                        status(phase="%s: cycle armed %.0f s after the live render" % (run, now - t_ready))
                    else:
                        cycles_skipped += 1
                        status(phase="%s: skipping a cycle that began %.0f s after render" % (run, now - t_ready))
                if armed is None:
                    continue
            if kind == "INFO":
                info_buf.append(name)
            elif kind == "BEGIN":
                begins[name] = now
                status(phase="%s: %s" % (run, name))
            elif kind == "DONE":
                infos["end"] = parse_info(info_buf).get("end")
                done = True
            elif kind == "MARK":
                step = name.rsplit("-", 1)[0]
                if any(k == "MARK" and n.rsplit("-", 1)[0] == step for k, n, _ in new[1:]):
                    skipped.append(dict(step=step, at=round(now - begins[step], 2)))
                    continue
                pose = dict((s[0], s[4]) for s in SEQUENCE)[step]
                rows = series.setdefault(step, [])
                wid = c.window()
                require(wid is not None, "window lost")
                f = out / "frames" / ("%s-%03d.png" % (step, len(rows)))
                tg = time.monotonic()
                c.grab(wid, f)
                raw = rgb(f)
                rows.append(dict(file=f.name, sha256=sha(f.read_bytes()), serverRaining=name.endswith("-r"),
                                 secondsAfterBegin=round(tg - begins[step], 2), epoch=round(time.time(), 2),
                                 frameMean=[round(sum(raw[k::3]) / (F.WIDTH * F.HEIGHT), 3) for k in range(3)],
                                 patches=measure(raw, pose)))
            elif kind == "READY":
                hinfo = parse_info(info_buf)
                info_buf = []
                i = NAMES.index(name)
                _, _, weather, lamp, pose, nframes = SEQUENCE[i]
                time.sleep(max(0.0, now + DWELL - time.monotonic()))
                wid, title = c.focus()
                frames = []
                for k in range(nframes):
                    f = out / "frames" / ("%s-%d.png" % (name, k))
                    tg = time.monotonic()
                    c.grab(wid, f)
                    frames.append((f, tg))
                    if k + 1 < nframes:
                        time.sleep(GAP)
                time.sleep(0.4)
                later = [e for e in events(c.text(), end) if e[0] in ("BEGIN", "DRIFT", "FAIL", "ABORT")]
                require(not later, "%s: scene changed before its frames were taken: %s" % (name, later))
                rows = []
                for f, tg in frames:
                    raw = rgb(f)
                    rows.append(dict(file=f.name, sha256=sha(f.read_bytes()), secondsAfterBegin=round(tg - begins[name], 2),
                                     secondsAfterReady=round(tg - now, 2), epoch=round(time.time(), 2),
                                     frameMean=[round(sum(raw[k::3]) / (F.WIDTH * F.HEIGHT), 3) for k in range(3)],
                                     patches=measure(raw, pose)))
                tag = "h%d" % i
                holds[name] = dict(weather=weather, lamp=lamp, pose=pose, title=title, server=hinfo.get(tag, {}), frames=rows)
                require(holds[name]["server"].get("rain") == (1 if weather == "rain" else 0), name + ": server weather")
                print(name, json.dumps({k: v for k, v in rows[0]["patches"].items() if "near" in k}), flush=True)
    finally:
        c.close()
    t = c.text()
    require(fatal(t) is None, str(fatal(t)))
    renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t).group(1).strip()
    require(lab.nvidia(renderer) and "All dimensions are saved" in t, "Clean NVIDIA shutdown not logged")
    require(tree(src) == src_manifest, "SOURCE WORLD CHANGED")
    require(digest(tree(snap)) == receipt["snapshot"]["digest"], "SNAPSHOT CHANGED")
    for n, h in originals.items():
        require(sha((orig / n).read_bytes()) == h, "Original Lab file changed: " + n)
    bad, light = saved_cells(world, END_LAMP)  # the next cycle may have begun (dry-a-on: lamp on as well)
    require(not bad, "saved clone differs after the run: %s" % bad[:3])
    lv = anvil.level(world)["Data"]
    (out / "complete.json").write_text(json.dumps(dict(
        renderer=renderer, glVersion=next((m.group(1).strip() for m in re.finditer(r"OpenGL Version: ([^\n]+)", t)), None),
        pack=pack.name, sha256=pack_sha, declaredHalfLives=halflife, normalModFiles=mods,
        world=dict(name=lab.WORLD, worldId=lab.WORLD_ID, seed=SEED, sourceDigest=digest(src_manifest), sourceUnchanged=True,
                   snapshotDigest=receipt["snapshot"]["digest"], snapshotUnchanged=True),
        savedAfterRun=dict(cellsExact=F.CELLS, lamp=END_LAMP, receiverLight=light,
                           levelWeather={k: lv.get(k) for k in ("raining", "rainTime", "thundering", "DayTime")}),
        originalLabFilesUnchanged=sorted(originals), playerUuid=PLAYER_UUID, datapackDigest=plan["datapackDigest"],
        width=F.WIDTH, height=F.HEIGHT, fovVertical=F.FOV, holds=holds, series=series, skippedMarks=skipped,
        armedSecondsAfterRender=round(armed - t_ready, 2), cyclesSkippedBeforeSettle=cycles_skipped,
        endServer=infos.get("end"), shaderFallback=False,
        note="display-referred 8-bit sRGB 11x11 patch means of ordinary Minecraft frames (x11grab of the private window); not GPU readback"),
        indent=1))
    return out


# ---------------------------------------------------------------- campaign


def next_name(prefix):
    i = 1
    while (HERE / ("%s-r%d" % (prefix, i))).exists():
        i += 1
    return "%s-r%d" % (prefix, i)


def completed(prefix):
    return [d.name for d in sorted(HERE.glob(prefix + "-r*")) if (d / "complete.json").is_file()]


def attempt(prefix, fn, *args):
    for k in range(2):
        name = next_name(prefix)
        runs = json.loads(STATUS.read_text()).get("runs", {}) if STATUS.exists() else {}
        runs[name] = dict(state="running", started=time.strftime("%H:%M:%S"), args=[str(a) for a in args])
        status(phase="running " + name, runs=runs)
        try:
            fn(*args, name)
            runs = json.loads(STATUS.read_text())["runs"]
            runs[name].update(state="complete", finished=time.strftime("%H:%M:%S"))
            status(runs=runs)
            return name
        except Exception as e:
            runs = json.loads(STATUS.read_text())["runs"]
            runs[name].update(state="failed", error="%s: %s" % (type(e).__name__, e), trace=traceback.format_exc()[-1500:])
            status(runs=runs)
            if k:
                raise


def campaign():
    status(phase="campaign", pid=os.getpid(), unit=os.environ.get("INVOCATION_ID"))
    if snapshot()[0] is None:
        attempt("build", lambda name: build(name))
    if not completed("base"):
        attempt("base", capture, BASE)
    subprocess.run([sys.executable, "-I", str(HERE / "measure.py")], check=False)
    if not completed(CANDIDATE_PREFIX):
        status(phase="waiting for " + CANDIDATE.name)
        deadline = time.time() + 6 * 3600
        while not CANDIDATE.is_file():
            require(time.time() < deadline, "Candidate never appeared")
            time.sleep(30)
        size = -1
        while size != CANDIDATE.stat().st_size:
            size = CANDIDATE.stat().st_size
            time.sleep(8)
        attempt(CANDIDATE_PREFIX, capture, CANDIDATE)
    subprocess.run([sys.executable, "-I", str(HERE / "measure.py")], check=False)
    status(phase="complete")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--dry-run"]:
        dry_run()
    elif a[:1] == ["build"] and len(a) == 2:
        build(a[1])
    elif a[:1] == ["capture"] and len(a) == 3:
        capture(a[1], a[2])
    elif a == ["campaign"]:
        campaign()
    else:
        sys.exit(__doc__)
