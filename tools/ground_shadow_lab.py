"""Capture ground shadows in the opt-in Lab world and restore the selected pack."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".audit"))
import land_shadow_runtime_2026_10_23 as lab

GAME = lab.GAME
CONTROL = GAME / "aqualumen-benchmark"
INSTANCE = GAME.parent / "instance.cfg"
SENTINEL = GAME / lab.SENTINEL
BENCH = ROOT / "build/aqualumen-benchmark-ground-3.jar"
SCENES = ["ground-noon", "ground-evening", "ground-sun-motion"]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def stopped():
    require(not lab.lab_java_processes(GAME), "Lab client is live")


def config_path(name):
    return INSTANCE if name == "instance.cfg" else GAME / name


def receipt(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)


def replace(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        os.fchmod(stream.fileno(), path.stat().st_mode & 0o777)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(stream.name, path)


def setup(out, pack, width, height, motion, clip, full_frame=False):
    stopped()
    lab.shared.owned_paths()
    lab.shared.world_marker()
    require(not SENTINEL.exists() and not any((CONTROL / n).exists() for n in
            ("request.properties", "opaque-fixture-journal.json")), "TEST is not idle")
    require({p.name for p in (GAME / "mods").glob("*.jar")} == lab.NORMAL_MODS, "Unexpected mod selection")
    require(lab.pairs((GAME / "config/iris.properties").read_bytes())["shaderPack"] == lab.ORDINARY, "Normal pack not selected")
    require(pack.suffix == ".zip" and not pack.is_symlink(), "Expected shader ZIP")
    sha = lab.sha(pack)
    dest = GAME / "shaderpacks" / pack.name
    require(not dest.is_symlink() and (not dest.exists() or lab.sha(dest) == sha), "Pack identity collision")
    require(not (dest.parent / (dest.name + ".txt")).exists(), "Pack has local option overrides")
    bench = GAME / "mods" / BENCH.name
    require(not bench.exists() and not bench.is_symlink(), "Benchmark destination already occupied")
    out.mkdir(parents=True, exist_ok=False)
    backup = Path(tempfile.mkdtemp(prefix="aqualumen-ground-", dir=Path.home()/".cache"))
    nonce = uuid.uuid4().hex[:12]
    changes = {"options.txt": (dict(lab.OPTIONS, maxFps="260", overrideWidth=str(width), overrideHeight=str(height)), ":"),
               "config/iris.properties": ({"shaderPack": pack.name}, "="),
               "instance.cfg": ({"MinecraftWinWidth": str(width), "MinecraftWinHeight": str(height)}, "=")}
    for name in (*lab.CONFIGS, "instance.cfg"):
        path = config_path(name)
        lab.sha(path)
        for folder in ("before", "during"):
            (backup/folder/name).parent.mkdir(parents=True, exist_ok=True)
        before = path.read_bytes()
        (backup/"before"/name).write_bytes(before)
        during = (lab.replace_values(before, *changes[name]) if name in changes else
                  lab.properties(dict(schema=2, world=lab.WORLD, world_id=lab.WORLD_ID, expected_pack=pack.name,
                                      expected_pack_sha256=sha, width=width, height=height, render_chunks=12,
                                      simulation_chunks=6, capture_motion=str(motion).lower(),ground_frame_strip=str(clip).lower(),water_frame_clip=str(full_frame).lower())))
        (backup/"during"/name).write_bytes(during)
    data = dict(backup=str(backup), pack=pack.name, packSHA=sha, addPack=not dest.exists(), bench=BENCH.name, benchSHA=lab.sha(BENCH),
                nonce=nonce, width=width, height=height, ordinarySave=lab.shared.prior.ordinary_tree(),
                mods=lab.tree(GAME/"mods"), configs={n:lab.sha(config_path(n)) for n in (*lab.CONFIGS,"instance.cfg")})
    receipt(out/"intent.json", data)
    stopped()
    if data["addPack"]:
        lab.shared.install_new(pack, dest, sha)
    lab.shared.install_new(BENCH, bench, data["benchSHA"])
    for name in data["configs"]:
        replace(config_path(name), (backup/"during"/name).read_bytes())
    with SENTINEL.open("x") as stream:
        stream.write(nonce)
    return data


def restore(out):
    stopped()
    d = json.loads((out/"intent.json").read_text())
    backup = Path(d["backup"])
    require(not (CONTROL/"opaque-fixture-journal.json").exists() and not (CONTROL/"request.properties").exists(),
            "Outstanding request or fixture journal")
    require(lab.shared.prior.ordinary_tree() == d["ordinarySave"], "Normal world changed")
    for name, expected in d["configs"].items():
        require(lab.sha(backup/"before"/name) == expected, "Backup mismatch")
        sep = ":" if name == "options.txt" else "="
        def values(data):
            props = lab.pairs(data, sep)
            return {k:v for k,v in props.items() if name != "instance.cfg" or k not in lab.LAUNCHER_TELEMETRY}
        current = values(config_path(name).read_bytes())
        require(any(current == values((backup/variant/name).read_bytes()) for variant in ("before","during")),
                "Unexpected change in " + name)
    benchname = d.get("bench","aqualumen-benchmark-ground-1.jar")
    require(benchname in ("aqualumen-benchmark-ground-1.jar", "aqualumen-benchmark-ground-2.jar", "aqualumen-benchmark-ground-3.jar", "aqualumen-benchmark-release-motion.jar", "aqualumen-benchmark-release-film.jar", BENCH.name), "Unrecognized TEST jar")
    owned = [(GAME/"mods"/benchname, d["benchSHA"])]
    if d["addPack"]:
        owned.append((GAME/"shaderpacks"/d["pack"], d["packSHA"]))
    require(all(not p.exists() or lab.sha(p)==s for p,s in owned) and
            (not SENTINEL.exists() or SENTINEL.read_text()==d["nonce"]), "TEST artifact identity changed")
    for path, _ in owned:
        if path.exists():
            path.rename(backup/path.name)
    if SENTINEL.exists():
        SENTINEL.rename(backup/SENTINEL.name)
    for name in d["configs"]:
        replace(config_path(name), (backup/"before"/name).read_bytes())
    require(all(lab.sha(config_path(n))==h for n,h in d["configs"].items()) and
            lab.tree(GAME/"mods")==d["mods"] and not SENTINEL.exists(), "Normal restoration differs")
    receipt(out/"restored.json", dict(configsExact=True, normalModsExact=True, ordinarySaveExact=True, benchmarkDisabled=True))


def control(*args):
    subprocess.run([sys.executable, str(ROOT/"tools/benchmark-control.py"), "--game", str(GAME), *args],
                   stdout=subprocess.DEVNULL, check=True)


def capture(out, data, scenes, seconds):
    private = Path(data["backup"])/"launcher.log"
    before = (GAME/"logs/latest.log").stat().st_mtime_ns
    with private.open("xb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        # Prism's GUI releases its instance launch slot after Java exits.
        # An immediate IPC launch during that interval may be acknowledged and dropped.
        time.sleep(3)
        proc = subprocess.Popen(["flatpak","run","--command=prismrun","org.prismlauncher.PrismLauncher",
                                 "--launch","Aqualumen Lab","--world",lab.WORLD], stdout=stream, stderr=subprocess.STDOUT,
                                env=dict(os.environ, DISPLAY=":1", XDG_RUNTIME_DIR="/run/user/1000",
                                         DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus"))
        run = "ground-" + data["nonce"]
        scene_dir = CONTROL/"runs"/run
        requested = False
        ready_since = None
        deadline = time.monotonic() + 250
        child_seen = False
        while True:
            time.sleep(1)
            # prismrun may hand the launch to an already-open Prism GUI and
            # return 0 before Java starts. The Lab client owns the lifecycle.
            active=lab.lab_java_processes(GAME)
            child_seen |= bool(active)
            if (child_seen and not active) or (not child_seen and proc.poll() not in (None, 0)):
                break
            logpath = GAME/"logs/latest.log"
            log = logpath.read_text(errors="replace") if logpath.exists() and logpath.stat().st_mtime_ns != before else ""
            server = log.find("Preparing start region for dimension minecraft:overworld")
            if not requested and server >= 0 and "Creating pipeline for dimension minecraft:overworld" in log[server:] and "Using shaderpack: "+data["pack"] in log and "NVIDIA GeForce RTX 3080 Ti" in log and "logged in with entity id" in log[server:] and len(lab.lab_java_processes(GAME)) == 1:
                if ready_since is None:
                    ready_since = time.monotonic()
                if time.monotonic()-ready_since < 3:
                    continue
                control("start","--run-id",run,"--scenes",*scenes,"--warmup","5","--sample",str(seconds),"--auto-quit")
                requested = True
                deadline = time.monotonic() + 90 + len(scenes)*(seconds+10)
                print("Requested", run, scenes, flush=True)
            if (scene_dir/"aborted.json").exists() or time.monotonic()>deadline:
                if not (CONTROL/"request.properties").exists():
                    control("quit")
                print("Waiting for guarded client exit", run, flush=True)
                end=time.monotonic()+45
                while lab.lab_java_processes(GAME) and time.monotonic()<end:
                    time.sleep(1)
                break
        require(proc.wait(timeout=45) == 0 and not lab.lab_java_processes(GAME) and (scene_dir/"complete.json").is_file(), "Game capture incomplete; private log " + str(private))
    shutil.copytree(scene_dir, out/"capture")
    manifest = json.loads((scene_dir/"run.json").read_text())
    require(manifest["world_id"]==lab.WORLD_ID and manifest["pack_sha256"]==data["packSHA"] and
            manifest["shader_active"] and not manifest["shader_fallback"] and "RTX 3080 Ti" in manifest["gl_renderer"]
            and manifest["framebuffer_resolution"]==[data["width"],data["height"]] and manifest["scenarios"]==scenes,
            "Capture identity mismatch")
    for scene in scenes:
        row=json.loads((scene_dir/(scene+".json")).read_text())
        require(row["scenario"] == scene and row["pack_sha256"] == data["packSHA"] and
                row["frames"] > 0 and row["camera_follows_local_player"] and row["window_focused"] and
                (scene_dir/(scene+".png")).is_file(), "Invalid camera capture: " + scene)
        if scene.startswith(("ground-", "air-", "opaque-")):
            clean=json.loads((scene_dir/(scene+"-fixture-cleanup.json")).read_text())
            require(clean["cleanup_complete"] and not clean["conflicts_preserved"], "Incomplete cleanup")
    print("Collected",run,flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--pack", type=Path)
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--static", action="store_true")
    parser.add_argument("--low-sun", action="store_true")
    parser.add_argument("--clip", action="store_true")
    parser.add_argument("--camera", action="store_true")
    parser.add_argument("--scenes", nargs="+", help="Explicit scene names validated by benchmark-control")
    parser.add_argument("--film", action="store_true", help="Save the entire game framebuffer in the 960x540 movement run")
    parser.add_argument("--motion", action="store_true", help="Record native frames in explicit scenes")
    parser.add_argument("--width", type=int, default=2560)
    parser.add_argument("--height", type=int, default=1440)
    args=parser.parse_args()
    if args.restore:
        restore(args.out)
    else:
        require(not args.out.exists() and not args.out.is_symlink(), "Output already exists")
        try:
            require(not args.camera or args.clip and not args.static and not args.low_sun, "Camera sweep requires --clip alone")
            scenes = (["ground-camera-motion"] if args.camera else ["ground-low-sun"] + (["ground-sun-motion"] if args.clip else []) if args.low_sun else
                      ["ground-sun-motion"] if args.clip else SCENES[:2] if args.static else SCENES)
            if args.scenes:
                require(not (args.camera or args.low_sun or args.clip or args.static), "Choose one scene selection")
                scenes=args.scenes
                if "underwater-shore-moving" in scenes:
                    BENCH=ROOT/"build/aqualumen-benchmark-release-motion.jar"
            if args.film:
                require(args.width==960 and args.height==540 and not args.motion and not args.clip and
                        set(scenes)<=set(("underwater-up-moving","underwater-shore-moving","ground-sun-motion")), "Invalid full-frame capture")
                BENCH=ROOT/"build/aqualumen-benchmark-release-film.jar"
            state=setup(args.out,args.pack,args.width,args.height,args.motion or "ground-sun-motion" in scenes and not args.clip and not args.film,args.clip,args.film)
            capture(args.out,state,scenes,10 if args.clip or "ground-sun-motion" in scenes else 6)
        finally:
            if (args.out/"intent.json").is_file() and not (args.out/"restored.json").exists() and not lab.lab_java_processes(GAME):
                restore(args.out)
