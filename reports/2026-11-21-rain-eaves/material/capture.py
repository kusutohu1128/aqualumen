"""Native shader telemetry. A private V2 copy waits for the focused client's swap key before weather starts."""
import fcntl
import gzip
import argparse
import statistics
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root/"reports/2026-11-21-indirect-light"))
import capture as base
sys.path.insert(0,str(here.parent/"fixture"))
import importlib.util
spec=importlib.util.spec_from_file_location("patio_layout",here.parent/"fixture/fixture.py")
patio=importlib.util.module_from_spec(spec)
spec.loader.exec_module(patio)
import anvil
sys.path.insert(0,str(root/"tools"))
import ground_shadow_lab as g
base.F=patio
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("name")
parser.add_argument("--time-pack",type=Path,help="Ordinary candidate to time at 1440p with the private V2 frame clock")
parser.add_argument("--sun",action="store_true",help="Measure a wet floor from the solar mirror direction with a removable side wall")
parser.add_argument("--weather-pack",type=Path,help="Record ordinary rain moving past an extinguished, warm or soul lantern")
parser.add_argument("--sun-break",action="store_true",help="Bracket the same vertical wall with open views after the clouds clear")
parser.add_argument("--particle-depth",action="store_true",help="Read actual particle positions, direct lamp radiance and traced source distance")
parser.add_argument("--particle-far",action="store_true",help="Observe falling particles around and beyond the lamp radius, from a second measured location")
options=parser.parse_args()
if options.particle_far:
    options.particle_depth=True
if options.particle_depth:
    assert not options.weather_pack
    options.weather_pack=root/"build/Aqualumen-rain-particle-depth.zip"
if options.sun_break:
    assert not options.sun
    options.sun=True
assert sum(map(bool,(options.sun,options.time_pack,options.weather_pack)))<=1
weather_movie=options.weather_pack is not None
timed=options.time_pack is not None
name=options.name
assert re.fullmatch(r"take-[0-9]+",name)
out=here/name
pack=(options.time_pack or options.weather_pack or root/"build/Aqualumen-rain-eaves-material-r4.zip").resolve()
assert g.lab.sha(pack)==json.loads((here/"packs.json").read_text())[pack.name]
orig=g.GAME.resolve()
source=orig/"saves"/g.lab.WORLD
runtime=json.loads((root/"reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
player="00000000000040008000000000000442"
env=dict(os.environ,DISPLAY=":1",__GLX_VENDOR_LIBRARY_NAME="nvidia",ALSOFT_DRIVERS="null")
lock=open(base.LOCK,"a+b")
fcntl.flock(lock,fcntl.LOCK_EX)
out.mkdir()
parent=Path(tempfile.mkdtemp(prefix="house-clock-rain-" if timed else "aql-rain-gauge-"))
game=parent/"minecraft"
for d in ["saves","config","mods","shaderpacks"]:
    (game/d).mkdir(parents=True)
clone=game/"saves"/g.lab.WORLD
g.lab.shared.world_marker()
with (source/"session.lock").open("r+b") as handle:
    fcntl.lockf(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest=base.copy_world(source,clone)
assert base.tree(clone)==manifest
marker=g.lab.pairs((clone/"aqualumen-world.properties").read_bytes())
assert marker["world_id"]==g.lab.WORLD_ID and marker["seed"]=="308060"
assert base.nbt(gzip.decompress((clone/"level.dat").read_bytes()))["Data"]["WorldGenSettings"]["seed"]==308060
probe=anvil.World(clone)
for pt in patio.cells("on"):
    at=patio.world(pt)
    assert probe.block(*at) in ("minecraft:air","minecraft:cave_air","minecraft:void_air",None) and probe.chunk(at[0]//16,at[2]//16) is not None,at
biome=probe.biome(*patio.world((4,2,9)))
assert biome and ("ocean" in biome or biome=="minecraft:plains"),biome
mods=g.lab.tree(orig/"mods")
for n in g.lab.NORMAL_MODS:
    shutil.copy(orig/"mods"/n,game/"mods")
clock=root/"build/aqualumen-door-frameclock-v2-test.jar"
clock_key=game/"config/house-frameclock.enabled"
if timed:
    shutil.copy(clock,game/"mods")
    clock_key.write_text(g.lab.WORLD_ID)
shutil.copy(pack,game/"shaderpacks")
for n in ["iris.properties","sodium-options.json"]:
    shutil.copy(orig/"config"/n,game/"config")
cfg=game/"config/iris.properties"
cfg.write_bytes(g.lab.replace_values(cfg.read_bytes(),{"shaderPack":pack.name},"="))
params=dict(g.lab.OPTIONS,maxFps="120",overrideWidth="1280",overrideHeight="720",chatVisibility="2",fov="0.0",pauseOnLostFocus="false",bobView="false",fovEffectScale="0.0",fullscreen="false")
width,height=(2560,1440) if timed else (1280,720)
if timed:
    params.update(maxFps="240",enableVsync="false",overrideWidth=str(width),overrideHeight=str(height))
(game/"options.txt").write_bytes(g.lab.replace_values((orig/"options.txt").read_bytes(),params,":"))
kit=clone/"datapacks/RainMaterialGauge"
assert not kit.exists()
def write(n, contents):
    p=kit/n
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(contents)
def fn(n,lines):
    write("data/gauge/function/"+n+".mcfunction","\n".join(lines)+"\n")
def w(pt):
    return " ".join(str(v) for v in patio.world(pt))
def region(box):
    lo,hi=box
    return w(lo)+" "+w(tuple(v-1 for v in hi))
write("pack.mcmeta",json.dumps({"pack":{"pack_format":48,"description":"Rain material probe in a disposable V2 world"}}))
write("data/minecraft/tags/function/tick.json",json.dumps({"values":["gauge:tick"]}))
fn("tick",["execute as @a[name="+patio.PLAYER+",tag=!gauge_start] run function gauge:start",
           "execute as @a[tag=gauge_armed,tag=!gauge_running] if items entity @s weapon.offhand minecraft:paper run function gauge:run"])
fn("start",["tag @s add gauge_start","gamerule doDaylightCycle false","gamerule doWeatherCycle false","gamerule doMobSpawning false",
            "gamerule doTileDrops false","difficulty peaceful","weather clear","time set 13000","gamemode creative @s",
            "forceload add 399 -441 413 -427","tp @s 404.5 69 -431.5","schedule function gauge:prepare 20t replace"])
fn("prepare",["execute if loaded 405 66 -435 run function gauge:build",
              "execute unless loaded 405 66 -435 run schedule function gauge:prepare 20t replace"])
fn("build",["fill "+region(box)+" "+block for box,block in patio.solids("on")]+[
    "tp "+patio.PLAYER+" 404.5 64 -430.5 180 0","item replace entity "+patio.PLAYER+" weapon.mainhand with minecraft:paper",
    "tag "+patio.PLAYER+" add gauge_armed","say AQW_ARMED"])
point=(8.5,1.0,9.5)
sun_pose=patio.look((11.10,4.8,9.5),point)
side_pose=patio.look((8.5,4.8,12.1),point)
rain_pose=patio.look((2.793,5.8,26.0),(6.5,4.44,5.5)) if options.particle_far else patio.POSES["a"]
if options.particle_far:
    rain_pose["yaw"]=round(rain_pose["yaw"],1)
    rain_pose["pitch"]=round(rain_pose["pitch"],1)
initial_pose=sun_pose if options.sun else rain_pose
fn("run",["tag @s add gauge_running","clear @s","gamemode spectator @s",base.tp(initial_pose),"say AQW_RUNNING",
          "schedule function gauge:s0 40t replace"])
glassbox="fill "+w((3,5,8))+" "+w((5,5,10))
lampcell="setblock "+w(patio.LAMP_CELL)+" "
pose=rain_pose
stages=[("dry",[],4),("rain_onset",["weather rain 600s"],5),("rise5",[],7),("rise12",[],13),
        ("rain25",[],7),("glass",[glassbox+" minecraft:glass"],6),("stone",[glassbox+" minecraft:stone"],6),
        ("open_again",[glassbox+" minecraft:air"],6),("lamp_off",[lampcell+"minecraft:air"],6),
        ("lamp_back",[lampcell+patio.LANTERN],5),("stop",["weather clear 600s"],9),("after9",[],15),
        ("after24",[],24),("after48",[],32),("after80",[],5)]
if weather_movie:
    stages=[("clear_lamp",[],10),("rain_starts",["weather rain 600s"],35),("warm_rain",[],12),
            ("lamp_off",[lampcell+"minecraft:air"],12),("soul_rain",[lampcell+"minecraft:soul_lantern[hanging=true]"],12),
            ("lamp_back",[lampcell+patio.LANTERN],10)]
if options.particle_far:
    stages=[("clear_lamp",[],10),("rain_starts",["weather rain 600s"],16),("warm_rain",[],9),
            ("lamp_off",[lampcell+"minecraft:air"],9),("soul_rain",[lampcell+"minecraft:soul_lantern[hanging=true]"],9),
            ("lamp_back",[lampcell+patio.LANTERN],9)]
if options.sun:
    wall="fill "+w((6,1,7))+" "+w((6,7,11))
    stages=[("day_dry",["time set 9000",lampcell+"minecraft:air"],4),
            ("cloud",["weather rain 600s"],42),("wet",[],6),
            ("wall",[wall+" minecraft:stone"],6),("clearing",["weather clear 600s"],7),
            ("unwall",[wall+" minecraft:air"],5),("side",[],5),("back",[],4)]
if options.sun_break:
    # Full rain removes direct Sun. Hold the clearing sky across the geometric comparison.
    stages=[("day_dry",["time set 9000",lampcell+"minecraft:air"],4),
            ("cloud",["weather rain 600s"],44),("overcast",[],4),
            ("parting",["weather clear 600s"],8),("sunlit",[],3),
            ("shade",[wall+" minecraft:stone"],4),("restored",[wall+" minecraft:air"],3),
            ("side",[],3),("back",[],4)]
if timed:
    stages=[("dry",[],16),("transition",["weather rain 600s"],34),("rain",[],16),
            ("lamp_off",[lampcell+"minecraft:air"],16),("done",[],2)]
elapsed=0;covered="minecraft:air";lamp=patio.LANTERN
for i,(state,commands,duration) in enumerate(stages):
    if state=="glass":covered="minecraft:glass"
    if state=="stone":covered="minecraft:stone"
    if state=="open_again":covered="minecraft:air"
    if state=="lamp_off":lamp=patio.AIR
    if state=="lamp_back":lamp=patio.LANTERN
    if state=="soul_rain":lamp="minecraft:soul_lantern[hanging=true]"
    if options.sun:
        pose=side_pose if state=="side" else sun_pose
        lamp=patio.AIR
    predicates=f"if block {w((4,5,9))} {covered} if block {w(patio.LAMP_CELL)} {lamp} if block {w((4,0,9))} minecraft:stone positioned "+" ".join(patio.fmt(v) for v in patio.feet(pose))+" if entity "+base.pose_selector(pose)
    if options.sun:
        expected_wall="minecraft:stone" if state in ("wall","clearing","shade") else "minecraft:air"
        predicates+=f" if block {w((6,4,9))} {expected_wall} if block {w((8,0,9))} minecraft:smooth_stone"
    fn("s"+str(i),commands+[base.tp(pose),"schedule function gauge:v"+str(i)+" 20t replace"]+(
        [f"schedule function gauge:s{i+1} {duration*20}t replace"] if i+1<len(stages) else []))
    fn("v"+str(i),["execute "+predicates+" run say AQW_READY_"+state])
    elapsed+=duration
args=[runtime["java"],"-Xms512m","-Xmx2600m","-XX:ActiveProcessorCount=4","-Dorg.lwjgl.openal.libname=libopenal.so.1",
      "-cp",":".join(runtime["cp"]),"net.fabricmc.loader.impl.launch.knot.KnotClient","--username",patio.PLAYER,"--version","1.21.1",
      "--gameDir",str(game),"--assetsDir",str(orig.parents[2]/"assets"),"--assetIndex","17","--uuid",player,"--accessToken","0",
      "--userType","legacy","--width",str(width),"--height",str(height),"--quickPlaySingleplayer",g.lab.WORLD]
if timed:
    args.insert(1,"-Daqualumen.house.frameclock="+str(game))
env["XDG_CACHE_HOME"]=str(parent/"cache")
if options.particle_depth:
    env["__GL_SHADER_DISK_CACHE_PATH"]=str(Path.home()/".cache/aqualumen-lab-shader-driver")
(out/"private-game.txt").write_text(str(game))
(out/"plan.json").write_text(json.dumps(dict(stages=stages,pose=patio.pose_record("a") if not options.sun else sun_pose,
    poses=({"mirror":sun_pose,"side":side_pose} if options.sun else {"particle":rain_pose} if options.particle_depth else {}),
    patches=patio.samples("a") if not options.sun else [dict(name="sun-mirror",world=patio.world(point),patch=[634,354,646,366],valid=True,block="minecraft:smooth_stone",exposed=True)],
    sourceDigest=base.digest(manifest),biome=biome,world_id=g.lab.WORLD_ID),indent=2))
log=out/"client.log"
samples={}
with log.open("xb") as stream:
    proc=subprocess.Popen(args,env=env,cwd=game,stdout=stream,stderr=stream)
    wid=None
    try:
        deadline=time.monotonic()+360; sent=None
        while len(samples)<len(stages):
            txt=log.read_text(errors="replace")
            if proc.poll() is not None or time.monotonic()>deadline: raise RuntimeError("capture timeout or closed client: "+str(list(samples)))
            if "/ERROR]" in txt or "reverting to default" in txt.lower():raise RuntimeError("Client logged an error")
            if not wid:
                ids=subprocess.run(["xdotool","search","--all","--onlyvisible","--pid",str(proc.pid),"--name","Minecraft"],env=env,text=True,capture_output=True).stdout.split()
                if len(ids)==1:wid=ids[0]
            if timed and "[HouseClock] disabled" in txt:
                raise RuntimeError("private frame clock disabled")
            if wid and sent is None and "AQW_ARMED" in txt and re.search(r"Creating pipeline for dimension minecraft:overworld.*?Started [1-9]\d* worker threads",txt,re.S):
                subprocess.run(["xdotool","windowfocus","--sync",wid],env=env,check=True,timeout=4)
                assert subprocess.check_output(["xdotool","getwindowfocus"],env=env,text=True).strip()==wid
                time.sleep(3)
                subprocess.run(["xdotool","key","--window",wid,"f"],env=env,check=True)
                sent=time.monotonic()
                deadline=sent+elapsed+42
            if sent and (match:=re.findall(r"\[Server\] AQW_READY_([a-z0-9_]+)",txt)):
                state=match[-1]
                if state not in samples:
                    wait_start=time.monotonic()
                    if timed:
                        samples[state]={"readyNs":time.monotonic_ns(),"readySeconds":wait_start-sent}
                        (out/"progress.json").write_text(json.dumps(samples,indent=2))
                        continue
                    if weather_movie:
                        # Let eye adaptation and the chunk meshes settle, then keep contiguous frames.
                        time.sleep(2.0)
                        clip=out/(state+".mkv")
                        subprocess.run(["ffmpeg","-v","error","-n","-f","x11grab","-framerate","8","-window_id",wid,
                            "-i",env["DISPLAY"],"-frames:v","32","-c:v","ffv1","-threads","2",str(clip)],env=env,check=True,timeout=10)
                        samples[state]=dict(readySeconds=wait_start-sent,captureSeconds=time.monotonic()-sent,sha256=g.lab.sha(clip))
                        (out/"progress.json").write_text(json.dumps(samples,indent=2))
                        continue
                    time.sleep(.22)
                    image=out/(state+".png")
                    subprocess.run(["ffmpeg","-v","error","-n","-f","x11grab","-window_id",wid,"-i",env["DISPLAY"],"-frames:v","1","-threads","1",str(image)],env=env,check=True,timeout=6)
                    assert base.png_size(image)==(1280,720)
                    samples[state]=dict(readySeconds=wait_start-sent,captureSeconds=time.monotonic()-sent,sha256=g.lab.sha(image))
                    (out/"progress.json").write_text(json.dumps(samples,indent=2))
            time.sleep(.12)
    finally:
        if timed:clock_key.unlink(missing_ok=True)
        if wid and proc.poll() is None:subprocess.run(["/tmp/aqualumen-wm-close",hex(int(wid))],env=env,timeout=6)
        try:proc.wait(timeout=24)
        except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=15)
txt=log.read_text(errors="replace")
assert "All dimensions are saved" in txt and "OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" in txt and "Using shaderpack: "+pack.name in txt
assert base.tree(source)==manifest and g.lab.tree(orig/"mods")==mods and not g.SENTINEL.exists()
extra={}
if timed:
    assert "[HouseClock] private frame clock ready; framebuffer 2560x1440" in txt
    assert not clock_key.exists() and params["renderDistance"]=="12"
    raw=game/"client-frames.csv"
    shutil.copyfile(raw,out/"client-frames.csv")
    times=list(map(int,raw.read_text().splitlines()))
    intervals={}
    for state in ("dry","rain","lamp_off"):
        start=samples[state]["readyNs"]+1_000_000_000
        end=start+10_000_000_000
        frames=[t for t in times if start<=t<=end]
        assert len(frames)>10 and frames[-1]-frames[0]>9_300_000_000
        ms=sorted((b-a)*1e-6 for a,b in zip(frames,frames[1:]))
        intervals[state]=dict(meanFPS=1000/statistics.mean(ms),p99Ms=ms[int(.99*len(ms))],maxMs=max(ms),intervals=len(ms),spanSeconds=(frames[-1]-frames[0])*1e-9)
    extra=dict(frameClock=intervals,resolution=[width,height],chunks=12,frameSource="Minecraft render-tail System.nanoTime",optInRemoved=True)
(out/"complete.json").write_text(json.dumps(dict(renderer="NVIDIA GeForce RTX 3080 Ti",pack=pack.name,sha256=g.lab.sha(pack),samples=samples,
    sourceUnchanged=True,modFiles=base.tree(game/"mods"),diagnosticShader=options.particle_depth or not (timed or weather_movie),**extra),indent=2))
