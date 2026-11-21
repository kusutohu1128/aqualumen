"""Run an ordinary (no recorder Mod) disposable offline client with a vanilla, world-local capture sequence."""

import sys, os, subprocess, tempfile, time, json, shutil, fcntl, hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "tools"))
import ground_shadow_lab as g

r = root / "reports/2026-11-21-carried-light"
pack = Path(sys.argv[1]).resolve()
out = r / sys.argv[2]
assert not out.exists() and pack.is_file()
out.mkdir()
orig = g.GAME
runtime = json.loads(
    (root / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text()
)
assets = orig.parents[2] / "assets"
labroot = Path(tempfile.mkdtemp(prefix="carried-natural-", dir=orig.parent))
game = labroot / "Aqualumen Lab/minecraft"
game.mkdir(parents=True)
(out / "private-game.txt").write_text(str(game))
for n in ["shaderpacks", "mods", "config", "saves"]:
    (game / n).mkdir()
src = orig / "saves" / g.lab.WORLD
g.lab.shared.world_marker()
with (src / "session.lock").open("r+b") as f:
    fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    shutil.copytree(
        src, game / "saves" / g.lab.WORLD, ignore=shutil.ignore_patterns("session.lock")
    )
world = game / "saves" / g.lab.WORLD
assert (
    g.lab.pairs((world / "aqualumen-world.properties").read_bytes())["world_id"]
    == g.lab.WORLD_ID
)
for n in g.lab.NORMAL_MODS:
    shutil.copy(orig / "mods" / n, game / "mods")
shutil.copy(pack, game / "shaderpacks")
for n in ["sodium-options.json", "iris.properties"]:
    if (orig / "config" / n).exists():
        shutil.copy(orig / "config" / n, game / "config")
(game / "config/iris.properties").write_bytes(
    g.lab.replace_values(
        (game / "config/iris.properties").read_bytes(), {"shaderPack": pack.name}, "="
    )
)
if os.environ.get("AQL_PHOTON_HELD") == "1":
    assert pack.name == "photon_v1.1.zip" and out.name == "photon-held"
    pref = game / "shaderpacks" / (pack.name + ".txt")
    pref.write_text("HANDHELD_LIGHTING=true\n")
    (out / "pack-options.txt").write_bytes(pref.read_bytes())
w, h = 1600, 900
(game / "options.txt").write_bytes(
    g.lab.replace_values(
        (orig / "options.txt").read_bytes(),
        dict(
            g.lab.OPTIONS,
            maxFps="120",
            overrideWidth=str(w),
            overrideHeight=str(h),
            pauseOnLostFocus="false",
            chatVisibility="2",
            mainHand=json.dumps(os.environ.get("AQL_SIDE", "right")),
        ),
        ":",
    )
)
kit = world / "datapacks/CarriedNatural"
func = kit / "data/carried/function"
func.mkdir(parents=True)
(kit / "pack.mcmeta").write_text(
    json.dumps(
        {"pack": {"pack_format": 48, "description": "Private Aqualumen visual checks"}}
    )
)
tags = kit / "data/minecraft/tags/function"
tags.mkdir(parents=True)
(tags / "tick.json").write_text('{"values":["carried:tick"]}')
player = "AqualumenOptics"
(func / "tick.mcfunction").write_text(
    "execute as @a[name=AqualumenOptics,tag=!carried_started] run function carried:start\n"
)
(func / "start.mcfunction").write_text(
    "tag @s add carried_started\ngamerule doDaylightCycle false\ngamerule doWeatherCycle false\ngamerule sendCommandFeedback false\ndifficulty peaceful\nweather clear\ngamemode creative @s\nschedule function carried:s0 480t replace\n"
)
c = json.loads((r / "cave-site.json").read_text())
forest = (208.5, 64, 355.5, 12.7, -2)
cave = tuple(c[k] for k in ("x", "y", "z", "yaw", "pitch"))
rows = []
for site, pose, tm, ls in [
    ("forest", forest, 9800, [("empty", "air", "air"), ("torch", "torch", "air")]),
    (
        "forest-night",
        forest,
        15500,
        [
            ("empty", "air", "air"),
            ("torch", "torch", "air"),
            ("soul", "soul_torch", "air"),
        ],
    ),
    (
        "cave",
        cave,
        15500,
        [
            ("empty", "air", "air"),
            ("torch", "torch", "air"),
            ("left", "air", "torch"),
            ("soul", "soul_torch", "air"),
            ("two", "torch", "soul_torch"),
            ("put-away", "air", "air"),
        ],
    ),
]:
    for name, main, off in ls:
        rows.append(
            dict(name=site + "-" + name, main=main, off=off, pose=pose, time=tm)
        )
dark = json.loads((r / "dark-cave-site.json").read_text())
darkPose = tuple(dark[k] for k in ("x", "y", "z", "yaw", "pitch"))
for k, main, off in [
    ("empty", "air", "air"),
    ("torch", "torch", "air"),
    ("offhand", "air", "torch"),
    ("soul", "soul_torch", "air"),
    ("two", "torch", "soul_torch"),
    ("put-away", "air", "air"),
]:
    rows.append(dict(name="mine-" + k, main=main, off=off, pose=darkPose, time=15500))
for key, pose in [("mine", darkPose), ("cave", cave)]:
    for t, label in [(6000, "noon"), (18000, "midnight")]:
        rows.append(
            dict(name=key + "-" + label, main="torch", off="air", pose=pose, time=t)
        )
for view in ["first", "rear", "front"]:
    rows.append(
        dict(
            name="forest-view-" + view,
            main="torch",
            off="air",
            pose=forest,
            time=15500,
            view=view,
        )
    )
subset = os.environ.get("AQL_SCENES", "")
if subset:
    chosen = {x["name"]: x for x in rows}
    rows = [chosen[name] for name in subset.split(",")]
for i, row in enumerate(rows):
    x, y, z, yaw, pitch = row["pose"]
    commands = [f"tp {player} {x} {y} {z} {yaw} {pitch}", f"time set {row['time']}"]
    verify = f"execute positioned {x} {y} {z} as @a[name={player},distance=..0.1]"
    for side, it in [("mainhand", row["main"]), ("offhand", row["off"])]:
        commands.append(
            f"item replace entity {player} weapon.{side} with minecraft:{it}"
        )
        verify += (
            f" unless items entity @s weapon.{side} *"
            if it == "air"
            else f" if items entity @s weapon.{side} minecraft:{it}"
        )
    commands.append(verify + " run say AQH_READY_" + row["name"] + "_OK")
    if i + 1 < len(rows):
        commands.append(f"schedule function carried:s{i + 1} 165t replace")
    (func / f"s{i}.mcfunction").write_text("\n".join(commands) + "\n")
(out / "plan.json").write_text(json.dumps(rows, indent=2))
env = dict(
    os.environ,
    DISPLAY=":1",
    XDG_RUNTIME_DIR="/run/user/1000",
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus",
    __GLX_VENDOR_LIBRARY_NAME="nvidia",
    ALSOFT_DRIVERS="null",
    XDG_CACHE_HOME=str(labroot / "cache"),
)
for k in [
    "JAVA_TOOL_OPTIONS",
    "JDK_JAVA_OPTIONS",
    "GALLIUM_DRIVER",
    "LIBGL_KOPPER_DRI2",
    "VK_DRIVER_FILES",
]:
    env.pop(k, None)
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
    player,
    "--version",
    "1.21.1",
    "--gameDir",
    str(game),
    "--assetsDir",
    str(assets),
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
shots = game / "screenshots"


def window():
    result = subprocess.run(
        [
            "xdotool",
            "search",
            "--all",
            "--onlyvisible",
            "--pid",
            str(p.pid),
            "--name",
            "Minecraft",
        ],
        env=env,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0 and len(result.stdout.split()) == 1:
        return result.stdout.strip()
    return None


log = out / "client.log"
with log.open("xb") as f:
    p = subprocess.Popen(java, stdout=f, stderr=f, env=env, cwd=game)
    try:
        activeView = 0
        for i, row in enumerate(rows):
            deadline = time.monotonic() + (130 if i == 0 else 28)
            marker = "AQH_READY_" + row["name"] + "_OK"
            while marker not in log.read_text(errors="replace"):
                if p.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Scene not acknowledged: " + marker)
                time.sleep(0.3)
            time.sleep(2.7)
            wid = window()
            assert wid
            subprocess.run(
                ["xdotool", "windowfocus", "--sync", wid],
                env=env,
                check=True,
                timeout=4,
            )
            wanted = ["first", "rear", "front"].index(row.get("view", "first"))
            if activeView != wanted:
                assert (
                    subprocess.check_output(
                        ["xdotool", "getwindowfocus"], env=env, text=True
                    ).strip()
                    == wid
                )
                for _ in range((wanted - activeView) % 3):
                    subprocess.run(["xdotool", "key", "F5"], env=env, check=True)
                    time.sleep(0.22)
                activeView = wanted
                time.sleep(0.65)
            target = out / (row["name"] + ".png")
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-n",
                    "-f",
                    "x11grab",
                    "-window_id",
                    wid,
                    "-i",
                    env["DISPLAY"],
                    "-frames:v",
                    "1",
                    "-threads",
                    "1",
                    str(target),
                ],
                env=env,
                check=True,
                timeout=5,
            )
            assert target.stat().st_size > 4000
            print(row["name"], flush=True)
    finally:
        wid = window()
        if wid and p.poll() is None:
            subprocess.run(
                ["/tmp/aqualumen-wm-close", hex(int(wid))], check=True, env=env
            )
        try:
            p.wait(timeout=24)
        except subprocess.TimeoutExpired:
            p.terminate()
            p.wait(timeout=10)
tx = log.read_text(errors="replace")
assert "[Render thread/ERROR]" not in tx and "disabling shaders" not in tx.lower()
assert (
    "OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" in tx
    and "Using shaderpack: " + pack.name in tx
    and "All dimensions are saved" in tx
)
(out / "complete.json").write_text(
    json.dumps(
        dict(
            renderer="NVIDIA GeForce RTX 3080 Ti",
            sha256=g.lab.sha(pack),
            images=len(rows),
            pack=pack.name,
            normalModFiles=sorted(g.lab.NORMAL_MODS),
            regionCopy=True,
            width=w,
            height=h,
            shaderFallback=any(
                v in tx.lower() for v in ("reverting to default", "disabling shaders")
            ),
        ),
        indent=2,
    )
)
