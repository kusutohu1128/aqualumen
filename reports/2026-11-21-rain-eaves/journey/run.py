"""One normal Minecraft day on a disposable copy of the packaged Rain Walk save."""
import argparse
import fcntl
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import string
import subprocess
import sys
import tempfile
import time
import uuid
from zipfile import ZipFile

import numpy as np
from PIL import Image
import hud

here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root/"tools"))
import ground_shadow_lab as g
sys.path.insert(0,str(root/"reports/2026-11-21-door-light/playable"))
from validate_world import parse_nbt
sys.path.insert(0,str(here.parent/"fixture"))
import anvil

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n")

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("run")
parser.add_argument("pack",type=Path)
parser.add_argument("world_sha")
parser.add_argument("--world-zip",type=Path,help="Immutable copy of the validated ordinary save")
parser.add_argument("--minutes",type=float,default=20.2)
parser.add_argument("--on-screen",action="store_true",help="Record a fully visible 1600x900 window directly from X11")
parser.add_argument("--tree-matrix",action="store_true",help="Test the mounted torch and the held soul lantern independently on the same oak")
args=parser.parse_args()
width,height=(1600,900) if args.on_screen else (2560,1440)
assert re.fullmatch(r"run-[0-9]+",args.run) and 1<=args.minutes<=25
pack=args.pack.resolve()
pack_sha=json.loads((here.parent/"material/packs.json").read_text())[pack.name]
world=(args.world_zip or root/"dist/Aqualumen-Rain-Walk.zip").resolve()
assert sha(pack)==pack_sha and sha(world)==args.world_sha
validation=json.loads((here.parent/"playable/validation.json").read_text())
assert not validation["failures"] and validation["settings"]["allowCommands"]==0
world_name="Aqualumen-Rain-Walk"
out=here/args.run
out.mkdir()
orig=g.GAME.resolve()
guard_files=["config/iris.properties","options.txt","config/sodium-options.json"]
original={n:sha(orig/n) for n in guard_files}
mods={n:sha(orig/"mods"/n) for n in g.lab.NORMAL_MODS}
lock=open("/tmp/aql-render21-1000.lock","a+b")
write(out/"status.json",{"stage":"awaiting render lock"})
fcntl.flock(lock,fcntl.LOCK_EX)
base=Path(tempfile.mkdtemp(prefix="aql-rain-journey-"))
game=base/"minecraft"
for d in ("saves","mods","config","shaderpacks"):(game/d).mkdir(parents=True)
for n in mods:shutil.copyfile(orig/"mods"/n,game/"mods"/n)
assert set(p.name for p in (game/"mods").iterdir())==g.lab.NORMAL_MODS
shutil.copyfile(pack,game/"shaderpacks"/pack.name)
for n in ["config/iris.properties","config/sodium-options.json"]:shutil.copyfile(orig/n,game/n)
iris=game/"config/iris.properties"
iris.write_bytes(g.lab.replace_values(iris.read_bytes(),{"shaderPack":pack.name},"="))
opt=dict(g.lab.OPTIONS,fullscreen="false",maxFps="60",enableVsync="false",overrideWidth=str(width),overrideHeight=str(height),
         rawMouseInput="false",mouseSensitivity="0.5",guiScale="2",lang="en_us",forceUnicodeFont="false",pauseOnLostFocus="false",
         fov="0.0",fovEffectScale="0.0",bobView="false",reducedDebugInfo="false")
(game/"options.txt").write_bytes(g.lab.replace_values((orig/"options.txt").read_bytes(),opt,":"))
with ZipFile(world) as z:
    assert sorted(z.namelist())==sorted(validation["archiveFiles"])
    for n in z.namelist():
        path=game/"saves"/n
        assert path.resolve().is_relative_to(game/"saves"/world_name)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(z.read(n))
save=game/"saves"/world_name
initial=parse_nbt(gzip.decompress((save/"level.dat").read_bytes()))["Data"]
assert initial["GameType"]==0 and not initial["allowCommands"] and not (save/"datapacks").exists()
guard_id=str(uuid.uuid4())
guard=base/"input-opt-in.json"
identity={"run":guard_id,"game":str(game.resolve()),"world":str(save.resolve()),"archive":sha(world),"seed":initial["WorldGenSettings"]["seed"]}
write(guard,identity)
write(out/"identity.json",identity)
runtime=json.loads((root/"reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
env=dict(os.environ,DISPLAY=":1",__GLX_VENDOR_LIBRARY_NAME="nvidia",ALSOFT_DRIVERS="null",XDG_CACHE_HOME=str(base/"cache"))
cmd=[runtime["java"],"-Xms512m","-Xmx2600m","-XX:ActiveProcessorCount=4","-Dorg.lwjgl.openal.libname=libopenal.so.1",
     "-cp",":".join(runtime["cp"]),"net.fabricmc.loader.impl.launch.knot.KnotClient","--username","RainPathWalker","--version","1.21.1",
     "--gameDir",str(game),"--assetsDir",str(orig.parents[2]/"assets"),"--assetIndex","17","--uuid","00000000000040008000000000000447",
     "--accessToken","0","--userType","legacy","--width",str(width),"--height",str(height),"--quickPlaySingleplayer",world_name]
logpath=out/"client.log"
observations=[]
actions=[]
video=None
reader=None
pixmap_owner=None
pixmap=None
grabber=str(root/"build/rain-walk-window")
start=None
wid=None
debug=False
proc=None
env["__GL_SHADER_DISK_CACHE_PATH"]=str(Path.home()/".cache/aqualumen-lab-shader-driver")

def x(*argv):
    return subprocess.check_output(["xdotool",*argv],env=env,timeout=5,text=True,stderr=subprocess.DEVNULL).strip()

def log():
    return logpath.read_text(errors="replace")

def input_guard():
    assert json.loads(guard.read_text())==identity and proc.poll() is None
    assert Path("/proc",str(proc.pid),"cwd").resolve()==game.resolve()
    assert x("getwindowpid",wid)==str(proc.pid) and x("getwindowfocus")==wid

def key(k):
    input_guard()
    x("key",k)

def motion(k,seconds):
    input_guard()
    x("keydown",k)
    try:time.sleep(seconds)
    finally:x("keyup",k)
    time.sleep(.21)

def debug_on(active):
    global debug
    if active!=debug:
        with (out/"hud-events.jsonl").open("a") as f:
            f.write(json.dumps({"seconds":time.monotonic()-start,"visible":active})+"\n")
        key("F3")
        time.sleep(.50 if active else .25)
        debug=active

def shot():
    if args.on_screen:
        data=subprocess.check_output(["ffmpeg","-v","error","-f","x11grab","-window_id",wid,"-i",env["DISPLAY"],
            "-frames:v","1","-threads","1","-pix_fmt","bgr0","-f","rawvideo","pipe:1"],env=env,timeout=6)
    else:
        data=subprocess.check_output([grabber,"read",pixmap,str(width),str(height)],env=env,timeout=6)
    assert len(data)==width*height*4
    return Image.frombytes("RGB",(width,height),data,"raw","BGRX")

def observe(label,save_frame=False):
    debug_on(True)
    for _ in range(5):
        im=shot()
        rgb=np.asarray(im)
        pos=hud.position(rgb)
        angles=hud.row_text(rgb,"Facing: ",string.ascii_letters+"0123456789-.()/ ")
        orient=re.search(r"\((-?[0-9.]+) / (-?[0-9.]+)\)",angles or "")
        if pos and orient:break
        time.sleep(.3)
    else:
        im.save(out/"unreadable-hud.png")
        raise RuntimeError("could not read vanilla position/orientation from F3")
    o={"label":label,"seconds":round(time.monotonic()-start,3),"xyz":pos,"angle":list(map(float,orient.groups())),"target":hud.target_block(rgb)}
    if save_frame:
        fname=f"{len(observations):03d}-{label}.jpg"
        im.resize((1280,720),Image.Resampling.LANCZOS).save(out/fname,quality=88)
        o["hudImage"]=fname
    observations.append(o)
    write(out/"positions.json",observations)
    debug_on(False)
    return o

def look(yaw,pitch):
    for _ in range(6):
        o=observe("aim")
        yaw0,pitch0=o["angle"]
        dyaw=(yaw-yaw0+180)%360-180
        if abs(dyaw)<.24 and abs(pitch-pitch0)<.24:return o
        input_guard()
        dx=round(max(-470,min(470,dyaw/.15)))
        dy=round(max(-250,min(250,(pitch-pitch0)/.15)))
        x("mousemove_relative","--",str(dx),str(dy))
        time.sleep(.24)
    return observe("aim-result")

def waypoint(z,label):
    for _ in range(6):
        o=observe(label)
        px,y,pz=o["xyz"]
        assert 2.1<px<4.9 and -60.3<y<-59.5,(label,o)
        assert abs(abs(o["angle"][0])-180)<.25,(label,"heading",o["angle"])
        if abs(pz-z)<.45:return o
        motion("w" if pz>z else "s",min(9.0,max(.065,abs(pz-z)/4.317)))
    raise RuntimeError("route stalled before "+label)

def image_at(label):
    shot().resize((1280,720),Image.Resampling.LANCZOS).save(out/(label+".jpg"),quality=91)

def record_tree_light_state(slot,label):
    key(slot)
    time.sleep(3.5)
    o=observe(label)
    image_at(label)
    return {"state":label,"seconds":o["seconds"],"xyz":o["xyz"],"angle":o["angle"],"target":o["target"]}

def torch_at_tree(label):
    o=waypoint(-8.5,"tree-interaction")
    px,y,pz=o["xyz"]
    dx,dz=5.77-px,-8.5-pz
    yaw=-math.degrees(math.atan2(dx,dz))
    pitch=math.degrees(math.atan2(y+1.62-(-58.5),math.hypot(dx,dz)))
    key("1") # empty hand
    aimed=look(yaw,pitch)
    if aimed["target"]!=(5,-59,-9):
        actions.append({"phase":label,"action":"torch interaction","state":"unconfirmed target","observed":aimed})
    else:
        matrix=[]
        if args.tree_matrix:
            matrix.append(record_tree_light_state("1","warm-only"))
            matrix.append(record_tree_light_state("4","both"))
        image_at(label+"-oak-torch-on")
        input_guard()
        x("click","1")
        time.sleep(2.0)
        empty=observe("trunk-after-torch-removal",True)
        if args.tree_matrix:
            matrix.append(record_tree_light_state("4","soul-only"))
            matrix.append(record_tree_light_state("1","both-off"))
            matrix.append(record_tree_light_state("4","soul-again"))
        image_at(label+"-oak-torch-off")
        if empty["target"]==(6,-59,-9):
            key("2") # ordinary torch stack
            input_guard()
            x("click","3")
            time.sleep(1.8)
            key("1")
            back=observe("torch-replaced",True)
            if args.tree_matrix:
                matrix.append(record_tree_light_state("4","both-again"))
                matrix.append(record_tree_light_state("1","warm-again"))
                assert all(s["angle"]==matrix[0]["angle"] and s["xyz"]==matrix[0]["xyz"] for s in matrix)
                assert all(s["target"]==((6,-59,-9) if s["state"] in ("soul-only","soul-again","both-off") else (5,-59,-9)) for s in matrix)
                write(out/"light-states.json",matrix)
            image_at(label+"-oak-torch-restored")
            actions.append({"phase":label,"seconds":round(time.monotonic()-start,2),"action":"mine and replace mounted torch","before":aimed["target"],"removed":empty["target"],"restored":back["target"]})
        else:actions.append({"phase":label,"action":"remove torch","result":empty})
    write(out/"actions.json",actions)
    look(180,10)

with logpath.open("xb") as stream:
    proc=subprocess.Popen(cmd,cwd=game,env=env,stdout=stream,stderr=stream)
    videolog=(out/"video.log").open("xb")
    try:
        deadline=time.monotonic()+430
        while "contact bridge initialized" not in log():
            assert proc.poll() is None and time.monotonic()<deadline and "disabling shaders" not in log().lower()
            time.sleep(.6)
        assert "Using shaderpack: "+pack.name in log() and "OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" in log()
        time.sleep(6)
        ids=x("search","--all","--onlyvisible","--pid",str(proc.pid),"--name","Minecraft").split()
        assert len(ids)==1
        wid=ids[0]
        x("windowfocus","--sync",wid)
        input_guard()
        assert "/ERROR]" not in log()
        start=time.monotonic()
        if args.on_screen:
            input_args=["-f","x11grab","-framerate","12","-window_id",wid,"-i",env["DISPLAY"]]
        else:
            pixmap_owner=subprocess.Popen([grabber,"name",wid],stdin=subprocess.PIPE,stdout=subprocess.PIPE,env=env,text=True)
            pixmap=pixmap_owner.stdout.readline().strip()
            assert pixmap.isdecimal() and pixmap_owner.poll() is None
            reader=subprocess.Popen([grabber,"read",pixmap,str(width),str(height),"12"],stdout=subprocess.PIPE,env=env)
            input_args=["-use_wallclock_as_timestamps","1","-f","rawvideo","-pixel_format","bgr0",
                "-video_size",f"{width}x{height}","-framerate","12","-i","pipe:0"]
        video=subprocess.Popen(["ffmpeg","-v","error","-n",*input_args,"-vf","scale=960:540:flags=lanczos",
            "-r","12","-fps_mode","cfr","-c:v","libx264","-preset","veryfast","-crf","25","-threads","3",
            "-pix_fmt","yuv420p",str(out/"ordinary-walk.mkv")],stdin=(reader.stdout if reader else subprocess.PIPE),stdout=videolog,stderr=videolog,env=env)
        if reader:reader.stdout.close()
        first=observe("spawn",True)
        image_at("patio-at-start")
        assert math.dist(first["xyz"],(3.5,-60,12.5))<1
        torch_at_tree("rain")
        tested_daylight=False
        circuit=0
        if args.tree_matrix:
            assert (out/"light-states.json").is_file()
            waypoint(10.5,"patio")
        while not args.tree_matrix and time.monotonic()-start<60*args.minutes:
            for target,place,slot in ((-45.5,"tunnel","4"),(-75.5,"bank","3"),(-8.5,"oak","2"),(10.5,"patio","1")):
                key(slot)
                waypoint(target,place)
                observe(place+"-arrive",circuit%4==0)
                if circuit in (0,4,9,14):
                    image_at(f"{circuit:02d}-{place}")
                time.sleep(2.0)
                assert video.poll() is None and proc.poll() is None
                write(out/"status.json",{"stage":"walking","seconds":time.monotonic()-start,"circuit":circuit+1,"at":place})
            circuit+=1
            if not tested_daylight and time.monotonic()-start>=900:
                torch_at_tree("daylight")
                tested_daylight=True
        end=observe("home",True)
        image_at("patio-at-end")
        length=time.monotonic()-start
    finally:
        if reader and reader.poll() is None:
            reader.terminate();reader.wait(timeout=8)
        if video and video.poll() is None:
            if args.on_screen:
                video.stdin.write(b"q\n")
                video.stdin.flush()
            video.wait(timeout=25)
        if pixmap_owner:
            pixmap_owner.stdin.close();pixmap_owner.wait(timeout=6)
        videolog.close()
        if not wid and proc.poll() is None:
            try:wid=x("search","--all","--onlyvisible","--pid",str(proc.pid),"--name","Minecraft").split()[-1]
            except (IndexError,subprocess.SubprocessError):pass
        if wid and proc.poll() is None:subprocess.run(["/tmp/aqualumen-wm-close",hex(int(wid))],env=env,timeout=8)
        try:proc.wait(timeout=30)
        except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=12)
        guard.unlink(missing_ok=True)

final=parse_nbt(gzip.decompress((save/"level.dat").read_bytes()))["Data"]
stats_files=list((save/"stats").glob("*.json"))
assert len(stats_files)==1
stats=json.loads(stats_files[0].read_text())["stats"]
walk_cm=stats.get("minecraft:custom",{}).get("minecraft:walk_one_cm",0)
assert "All dimensions are saved" in log() and "/ERROR]" not in log() and (args.tree_matrix or length>=args.minutes*60) and video.returncode==0
assert walk_cm>(3500 if args.tree_matrix else 1200*args.minutes) and not final["allowCommands"] and final["GameType"]==0
assert sha(world)==args.world_sha and all(sha(orig/n)==v for n,v in original.items())
assert all(sha(orig/"mods"/n)==v for n,v in mods.items()) and not g.SENTINEL.exists()
movie=out/"ordinary-walk.mkv"
duration=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(movie)],text=True))
assert duration>=(length-3 if args.tree_matrix else 60*args.minutes-2)
record={"renderer":"NVIDIA GeForce RTX 3080 Ti","pack":pack.name,"sha256":pack_sha,"worldSHA":args.world_sha,"end":end,
        "seconds":length,"treeMatrix":args.tree_matrix,"videoSeconds":duration,"circuits":circuit,"measuredWalkMetres":walk_cm/100,"stats":stats,
        "initial":{"time":initial["DayTime"],"raining":initial["raining"]},"final":{"time":final["DayTime"],"raining":final["raining"]},
        "torchCellAtEnd":anvil.World(save).block(5,-59,-9),"actions":actions,"cleanExit":True,"mods":mods,"originalUnchanged":True,
        "renderResolution":[width,height],"videoResolution":[960,540],"captureHz":12,"renderChunks":12,"benchmarkMod":False}
write(out/"complete.json",record)
write(out/"status.json",{"stage":"complete","seconds":length,"circuits":circuit})
