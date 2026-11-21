"""Reload an archived house, then change only one lamp in its private, opt-in copy."""
import fcntl
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

here = Path(__file__).resolve().parent
report = here.parent
root = report.parents[1]
sys.path.insert(0, str(root / "reports/2026-11-21-indirect-light"))
spec = importlib.util.spec_from_file_location("door_control_capture", report / "capture.py")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
capture.configure()
C, H = capture.C, capture.H
sys.path.insert(0, str(root / "tools"))
import ground_shadow_lab as g

runtime = json.loads((root / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
orig = g.GAME.resolve()
receipt = json.loads((report / "receiver-readback/complete.json").read_text())
old = Path((report / "receiver-readback/private-game.txt").read_text().strip())
assert old.resolve() == old and old.parents[2] == orig.parent and old.parents[1].name.startswith("indirect-optics-")
src = old / "saves" / g.lab.WORLD
assert g.lab.pairs((src / "aqualumen-world.properties").read_bytes())["world_id"] == g.lab.WORLD_ID
assert sys.argv[1:] in ([], ["--ordinary"], ["--finish"])
ordinary = bool(sys.argv[1:])
if ordinary:
    pack = root / "dist/Aqualumen-1.6.0.zip"
    assert g.lab.sha(pack) == json.loads((report / "normal-smoke.json").read_text())["packSHA"]
else:
    pack = root / "build" / receipt["pack"]
    assert g.lab.sha(pack) == receipt["sha256"]
lock = open(C.LOCK, "a+b")
fcntl.flock(lock, fcntl.LOCK_EX)
out = here / ("ordinary-finish" if sys.argv[1:]==["--finish"] else "ordinary" if ordinary else "settled")
out.mkdir()
parent = Path(tempfile.mkdtemp(prefix="house-clock-", dir=orig.parent))
game = parent / "minecraft"
game.mkdir()
for folder in ["mods","config","shaderpacks","saves"]:
    (game / folder).mkdir()
world = game / "saves" / g.lab.WORLD
with (src / "session.lock").open("r+b") as sessionlock:
    fcntl.lockf(sessionlock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    manifest = C.copy_world(src, world)
assert C.tree(world) == manifest
(out / "private-game.txt").write_text(str(game))
for name, h in receipt["normalModFiles"].items():
    assert g.lab.sha(old / "mods" / name) == h
    shutil.copy(old / "mods" / name, game / "mods")
shutil.copytree(old / "config", game / "config", dirs_exist_ok=True)
shutil.copy(old / "options.txt", game / "options.txt")
iris = game / "config/iris.properties"
assert g.lab.pairs(iris.read_bytes())["shaderPack"] == receipt["pack"]
if ordinary:
    iris.write_bytes(g.lab.replace_values(iris.read_bytes(), {"shaderPack":pack.name}, "="))
shutil.copy(pack, game / "shaderpacks")
if not ordinary:
    (game / "config/house-frameclock.enabled").write_text(g.lab.WORLD_ID)

    # Reuse the confirmed UUID/path/seed guard, calling our read-only sampler only after it succeeds.
    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp)
        recorder = (report / "timing/Recorder.java").read_text()
        anchor = "output.write(Long.toString(tick));"
        assert recorder.count(anchor) == 1
        (build / "Recorder.java").write_text(recorder.replace(anchor, "CellLight.sample(client,tick);"))
        javac = Path(runtime["java"]).with_name("javac")
        subprocess.run([str(javac), "-proc:none","-cp",":".join(runtime["cp"]),"-d",tmp,
                        str(build/"Recorder.java"), str(here/"CellLight.java"),
                        str(root/"tools/benchmark-mod/dev/aqualumen/bench/FrameMixin.java")],check=True)
        from zipfile import ZipFile
        with ZipFile(root/"build/aqualumen-door-frameclock-v2-test.jar") as base, ZipFile(game/"mods/private-sky-reader.jar","x") as jar:
            for name in ("fabric.mod.json","houseclock.mixins.json"):
                jar.writestr(name,base.read(name))
            for cls in build.rglob("*.class"):
                jar.write(cls, cls.relative_to(build))

# Disable the previous capture functions in the new copy only. Pending old scheduled IDs become no-ops.
kit = world / "datapacks/DoorLight"
assert (kit/"data/aqd/function/tick.mcfunction").is_file()
for f in (kit/"data/aqd/function").glob("*.mcfunction"):
    f.write_text("# archived capture disabled in this copy\n")
functions = kit/"data/aqd/function"
def function(n, commands):
    (functions/(n+".mcfunction")).write_text("\n".join(commands)+"\n")
function("tick",["execute as @a[name="+H.PLAYER+",tag=!cells_begin] if loaded 406 161 -400 run function aqd:cellsinit"])
function("cellsinit",["tag @s add cells_begin", C.tp(H.POSES["main"]),
                      "setblock "+capture.D.w(H.DOOR_UPPER)+" air","setblock "+capture.D.w(H.DOOR_LOWER)+" air",
                      "setblock "+capture.D.w(H.SOUL_CELL)+" air", "schedule function aqd:cellson 20t replace"])
for n, value, other in [("on",H.WARM,"off"),("off",H.AIR,"on")]:
    function("cells"+n, ["setblock "+capture.D.w(H.WARM_CELL)+" "+value,
                         "schedule function aqd:verify"+n+" 80t replace",
                         "schedule function aqd:cells"+other+" 260t replace"])
    function("verify"+n,["execute if block "+capture.D.w(H.WARM_CELL)+" "+value
                          +" if block 406 160 -400 minecraft:smooth_stone positioned "+" ".join(H.fmt(v) for v in H.feet(H.POSES["main"]))+" if entity "+C.pose_selector(H.POSES["main"])
                          +" run say AQC_"+n+"_READY"])
if ordinary:
    # Mutate only the lights and the two halves of the central door. The house is already saved.
    states = ["open-warm","off-open","closed-soul","closed-both","open-both","open-soul","off-closed","closed-warm","open-repeat"]
    if sys.argv[1:]==["--finish"]:
        states=["closed-warm","open-warm","open-repeat"]
    pose = H.POSES["main"]
    function("cellsinit",["tag @s add cells_begin", C.tp(pose), "schedule function aqd:play0 20t replace"])
    for i, name in enumerate(states):
        role = H.role(name)
        function("play"+str(i),[C.tp(pose)]+capture.D.set_dynamic(role)+[
            f"schedule function aqd:confirm{i} 80t replace",
            f"schedule function aqd:play{(i+1)%len(states)} 220t replace"])
        checks = ["if block "+capture.D.w(c)+" "+b for c,b in H.dynamic_blocks(role).items()]
        checks += ["if block 406 160 -400 minecraft:smooth_stone",
                   "positioned "+" ".join(H.fmt(v) for v in H.feet(pose)),"if entity "+C.pose_selector(pose)]
        function("confirm"+str(i),["execute "+" ".join(checks)+" run say AQC_"+name+"_READY"])
else:
    states=["on","off"]
env=dict(os.environ, DISPLAY=":1",__GLX_VENDOR_LIBRARY_NAME="nvidia",ALSOFT_DRIVERS="null",XDG_CACHE_HOME=str(parent/"cache"))
args=[runtime["java"],"-Xms512m","-Xmx2600m","-XX:ActiveProcessorCount=4","-Daqualumen.house.frameclock="+str(game),
      "-Dorg.lwjgl.openal.libname=libopenal.so.1","-cp",":".join(runtime["cp"]),"net.fabricmc.loader.impl.launch.knot.KnotClient",
      "--username",H.PLAYER,"--version","1.21.1","--gameDir",str(game),"--assetsDir",str(orig.parents[2]/"assets"),
      "--assetIndex","17","--uuid",C.PLAYER_UUID,"--accessToken","0","--userType","legacy",
      "--width","1280","--height","720","--quickPlaySingleplayer",g.lab.WORLD]
log=out/"client.log"
samples=[]
with log.open("xb") as stream:
    proc=subprocess.Popen(args,cwd=game,env=env,stdout=stream,stderr=stream)
    wid=None
    try:
        start=time.monotonic(); offset=None
        while len(samples)<(len(states) if ordinary else 4):
            assert time.monotonic()-start<310 and proc.poll() is None
            txt=log.read_text(errors="replace")
            if "[HouseClock] disabled" in txt: raise RuntimeError(txt.split("[HouseClock] disabled")[-1][:160])
            if not wid:
                ids=subprocess.run(["xdotool","search","--all","--onlyvisible","--pid",str(proc.pid),"--name","Minecraft"],env=env,text=True,capture_output=True).stdout.split()
                if ids: wid=ids[-1]
            if wid and (ordinary or "[HouseClock] private frame clock ready" in txt) and re.search(r"Creating pipeline for dimension minecraft:overworld.*?Started [1-9]\d* worker threads",txt,re.S):
                if offset is None: offset=len(txt)
                matches=list(re.finditer(r"\[Server\] AQC_([a-z-]+)_READY",txt[offset:]))
                if matches:
                    match=matches[-1]; state=match[1]; offset+=match.end()
                    if ordinary and any(row["state"]==state for row in samples): continue
                    assert state in states
                    time.sleep(2)
                    name=f"{len(samples)}-{state}.png"
                    subprocess.run(["ffmpeg","-v","error","-n","-f","x11grab","-window_id",wid,"-i",env["DISPLAY"],"-frames:v","1","-threads","1",str(out/name)],env=env,check=True,timeout=8)
                    txt=log.read_text(errors="replace")
                    row=dict(state=state,file=name,sha256=g.lab.sha(out/name))
                    if not ordinary:
                        line=[s for s in txt.splitlines() if "[HouseCells]" in s][-1]
                        assert ("minecraft:lantern" in line)==(state=="on") and ("minecraft:air" in line)==(state=="off")
                        row["clientCells"]=line.split("[HouseCells] ")[1]
                    samples.append(row)
            time.sleep(.18)
    finally:
        if wid and proc.poll() is None: subprocess.run(["/tmp/aqualumen-wm-close",hex(int(wid))],env=env,timeout=5)
        try: proc.wait(timeout=24)
        except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=12)
        (game/"config/house-frameclock.enabled").unlink(missing_ok=True)
txt=log.read_text(errors="replace")
assert "All dimensions are saved" in txt and "OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" in txt
assert C.tree(src)==manifest and set(s["state"] for s in samples)==set(states)
assert "Using shaderpack: "+pack.name in txt and "reverting to default" not in txt.lower() and "/ERROR]" not in txt
(out/"complete.json").write_text(json.dumps(dict(renderer=receipt["renderer"],pack=pack.name,sha256=g.lab.sha(pack),
    samples=samples,normalModsOnly=ordinary,grid="x403..408 inside z-403..-398, y161, sky/block",sourceWorldDigest=C.digest(manifest),
    sourceUnchanged=True,worldUUID=g.lab.WORLD_ID,privateOptInRemoved=True),indent=2))
