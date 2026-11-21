"""Run an ordinary (no recorder Mod) disposable offline client with a vanilla, world-local capture sequence."""

import sys, os, subprocess, tempfile, time, json, shutil, fcntl, hashlib
from pathlib import Path

render_lock = open("/tmp/aql-render21-" + str(os.getuid()) + ".lock", "a+b")
fcntl.flock(render_lock, fcntl.LOCK_EX)
root = Path.cwd()
sys.path.insert(0, str(root / "tools"))
import ground_shadow_lab as g

r = root / "reports/2026-11-21-mob-light"
pack = Path(sys.argv[1]).resolve()
out = r / sys.argv[2]
assert not out.exists() and pack.is_file()
out.mkdir()
orig = g.GAME
runtime = json.loads(
    (root / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text()
)
assets = orig.parents[2] / "assets"
labroot = Path(tempfile.mkdtemp(prefix="entity-optics-", dir=orig.parent))
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
w, h = 1280, 720
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
kit = world / "datapacks/EntityLight"
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
    "tag @s add carried_started\ngamerule doDaylightCycle false\ngamerule doWeatherCycle false\ngamerule sendCommandFeedback false\ndifficulty peaceful\nweather clear\ngamemode spectator @s\nforceload add 403 -413 410 -405\ntp @s 409.48 151 -405.95 153.8 7\nschedule function carried:s0 2000t replace\n"
)
# All writes run only in the new, UUID-checked disposable world. Validate the air volume before building.
setup = [
    "scoreboard objectives add aql_probe dummy",
    "scoreboard players set #clear aql_probe 1",
]
for x in range(403, 411):
    for y in range(150, 156):
        for z in range(-413, -404):
            setup.append(
                f"execute unless block {x} {y} {z} minecraft:air run scoreboard players set #clear aql_probe 0"
            )
setup += ["execute if score #clear aql_probe matches 1 run function carried:build"]
(func / "setup.mcfunction").write_text("\n".join(setup) + "\n")
(func / "build.mcfunction").write_text(
    "fill 403 150 -413 410 155 -405 minecraft:white_concrete hollow\nfill 403 150 -413 410 150 -405 minecraft:smooth_stone\nexecute if block 403 150 -413 minecraft:smooth_stone if block 410 155 -405 minecraft:white_concrete if block 406 152 -413 minecraft:white_concrete if block 406 152 -410 minecraft:air run scoreboard players set #ready aql_probe 1\n"
)
sel = "@e[type=minecraft:cow,tag=aq_entity_optical,limit=1]"
pose = (409.48, 151, -405.95, 153.8, 7)
x, y, z, yaw, pitch = pose
rows = []
states = [
    ("lamp-empty", "lantern", None),
    ("cow-near", "lantern", (405.5, 151, -409.35)),
    ("cow-stepped", "lantern", (406.3, 151, -409.35)),
    ("cow-far", "lantern", (408.8, 151, -408.0)),
    ("removed", "lantern", None),
    ("unlit", "air", None),
    ("unlit-cow", "air", (405.5, 151, -409.35)),
]
walk = os.environ.get("AQL_MOB_WALK") == "1"
if walk:
    states = [("walk", "lantern", (404.7, 151, -410.4))]
for i, (name, lamp, mob) in enumerate(states):
    row = dict(name=name, lamp=lamp, mob=mob, pose=pose, time=18000)
    rows.append(row)
    pre = ["function carried:setup"] if i == 0 else []
    cmds = [
        f"tp {player} {x} {y} {z} {yaw} {pitch}",
        "time set 18000",
        f"setblock 404 151 -407 minecraft:{lamp}",
    ]
    if mob:
        xyz = " ".join(map(str, mob))
        cmds += [
            f'execute unless entity {sel} run summon minecraft:cow {xyz} {{Tags:["aq_entity_optical"],NoAI:1b,PersistenceRequired:1b,Silent:1b,Rotation:[90f,0f]}}',
            f"tp {sel} {xyz} 90 0",
        ]
        mobCheck = f" positioned {xyz} if entity @e[type=minecraft:cow,tag=aq_entity_optical,distance=..0.05,limit=1]"
    else:
        cmds += [f"execute if entity {sel} run kill {sel}"]
        mobCheck = f" unless entity {sel}"
    # A killed mob can remain for its death animation. Validate after 2s.
    (func / f"check{i}.mcfunction").write_text(
        f"execute if score #ready aql_probe matches 1 positioned {x} {y} {z} if entity @a[name={player},distance=..0.05] if block 406 152 -413 minecraft:white_concrete if block 405 150 -409 minecraft:smooth_stone if block 406 152 -410 minecraft:air if block 404 151 -407 minecraft:{lamp}{mobCheck} run say AQH_READY_{name}_OK\n"
    )
    if walk:
        cmds += [
            f"gamemode creative {player}",
            f"item replace entity {player} weapon.mainhand with minecraft:wheat",
            "schedule function carried:release 120t replace",
        ]
        (func / "release.mcfunction").write_text(
            f"data merge entity {sel} {{NoAI:0b}}\nsay AQM_AI_START\nfunction carried:trajectory\nschedule function carried:walkend 140t replace\n"
        )
        (func / "trajectory.mcfunction").write_text(
            f'tellraw @a [{{"text":"AQM_POSITION "}},{{"nbt":"Pos","entity":"{sel}"}}]\nexecute if entity {sel} run schedule function carried:trajectory 5t replace\n'
        )
        (func / "walkend.mcfunction").write_text(
            f"say AQM_REMOVING\nkill {sel}\nitem replace entity {player} weapon.mainhand with minecraft:air\nschedule clear carried:trajectory\n"
        )
        # Command feedback is required in the private server log to retain positions.
        cmds += ["gamerule logAdminCommands true"]
    cmds.append(f"schedule function carried:check{i} 40t replace")
    if i + 1 < len(states):
        cmds.append(f"schedule function carried:s{i + 1} 170t replace")
    (func / f"s{i}.mcfunction").write_text(
        "\n".join(
            pre
            + ["execute if score #ready aql_probe matches 1 run " + cmd for cmd in cmds]
        )
        + "\n"
    )
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
            deadline = time.monotonic() + (205 if i == 0 else 28)
            marker = "AQH_READY_" + row["name"] + "_OK"
            while marker not in (text := log.read_text(errors="replace")):
                if (
                    "disabling shaders" in text.lower()
                    or "reverting to default" in text.lower()
                    or "[Render thread/ERROR]" in text
                ):
                    raise RuntimeError(
                        "Minecraft pipeline error: see private client.log"
                    )
                if p.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Scene not acknowledged: " + marker)
                time.sleep(0.3)
            assert "0.2.0 contact bridge initialized" in log.read_text(
                errors="replace"
            ), "World renderer still loading"
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
            if walk:
                video = out / "wheat-follow.mp4"
                subprocess.run(
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-n",
                        "-f",
                        "x11grab",
                        "-framerate",
                        "25",
                        "-window_id",
                        wid,
                        "-i",
                        env["DISPLAY"],
                        "-t",
                        "14",
                        "-c:v",
                        "libx264",
                        "-threads",
                        "3",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "17",
                        "-pix_fmt",
                        "yuv420p",
                        "-movflags",
                        "+faststart",
                        str(video),
                    ],
                    env=env,
                    check=True,
                    timeout=24,
                )
                assert "AQM_REMOVING" in log.read_text(errors="replace")
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
