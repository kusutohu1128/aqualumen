"""Record a short OpenGL trace of one real private Minecraft JVM at the saved stone camp."""
import argparse
import fcntl
from hashlib import sha256
import json
import os
import re
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from zipfile import ZipFile

from make_rows import HERE, ROOT, WORK
sys.path.insert(0,str(ROOT/"tools"))
sys.path.insert(0,str(HERE.parent/"2026-11-22-gpu-profile"))
from run import GAME, LAB, inspect_gpu, lab_check

WOOD=HERE.parent/"2026-11-21-animal-light/woodland"
SHIP=ROOT/"dist/Aqualumen-Torch-Shadow-Rows.zip"
SHIP_SHA="d9a740d78c612634a5c197bb001a3bcc250f83d0e891d0cbb90363de334d7968"
SAVE_SHA="bda0c610007db06e43bc21c8a52273de66606661c066b4e94b20070d7a3914ce"

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return sha256(path.read_bytes()).hexdigest()

def owned_java(game):
    for link in Path("/proc").glob("[0-9]*/cwd"):
        try:
            if link.readlink()!=game or (link.parent/"comm").read_text().strip()!="java": continue
            parts=(link.parent/"cmdline").read_bytes().split(b"\0")
            if b"--gameDir" in parts and parts[parts.index(b"--gameDir")+1]==os.fsencode(game):
                return int(link.parent.name)
        except (FileNotFoundError,PermissionError,ProcessLookupError):
            continue
    return None

def prepare(game):
    run=WOOD/"row-scan-camp-walk"
    prior=Path(read(run/"identity.json")["game"]).resolve(strict=True)
    assert prior.is_relative_to("/tmp") and prior.name=="minecraft"
    save=read(run/"save.json")
    archive=ROOT/save["archive"]
    assert sha(archive)==save["sha256"]==SAVE_SHA and save["seed"]==308060 and save["allowCommands"]==0
    assert sha(SHIP)==SHIP_SHA
    game.mkdir()
    for name in ("mods","config","saves","shaderpacks"):
        (game/name).mkdir()
    for name in ("options.txt","config/iris.properties","config/sodium-options.json"):
        shutil.copyfile(prior/name,game/name)
    from ground_shadow_lab import lab
    iris=game/"config/iris.properties"
    iris.write_bytes(lab.replace_values(iris.read_bytes(),{"shaderPack":SHIP.name},"="))
    for name in LAB["activeMods"]+["aqualumen-lighting-compiler-0.3.0.jar"]:
        src=prior/"mods"/name
        expected=LAB["compilerSha256"] if "compiler" in name else sha(GAME/"mods"/name)
        assert sha(src)==expected
        shutil.copyfile(src,game/"mods"/name)
    shutil.copyfile(SHIP,game/"shaderpacks"/SHIP.name)
    with ZipFile(archive) as z:
        assert set(z.namelist())=={save["folder"]+"/"+n for n in save["members"]}
        for n,digest in save["members"].items():
            path=(game/"saves"/save["folder"]/n).resolve()
            assert path.is_relative_to(game/"saves"/save["folder"])
            data=z.read(save["folder"]+"/"+n)
            assert sha256(data).hexdigest()==digest
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
    return save["folder"]

def summarize(db,pid):
    with sqlite3.connect(db.as_uri()+"?mode=ro",uri=True) as c:
        match=" join PROCESSES p on p.globalPid=(a.globalTid & ~16777215) "
        sql="from OPENGL_API a"+match+" where p.pid=?"
        n,b,e=c.execute("select count(*),min(start),max(end) "+sql,(pid,)).fetchone()
        assert n and e>b, (pid,n)
        calls=c.execute("select s.value,count(*),sum(a.end-a.start)/1e6 from OPENGL_API a"+match+
                "join StringIds s on s.id=a.nameId where p.pid=? group by s.value order by count(*) desc",(pid,)).fetchall()
        threads=c.execute("select (a.globalTid & 16777215),count(*) "+sql+" group by a.globalTid order by count(*) desc",(pid,)).fetchall()
        tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
        osrt=[]
        if "OSRT_API" in tables:
            osrt=c.execute("select s.value,count(*),sum(a.end-a.start)/1e6 from OSRT_API a"+match+
                    "join StringIds s on s.id=a.nameId where p.pid=? and (a.globalTid & 16777215)=? group by s.value order by sum(a.end-a.start) desc limit 6",
                    (pid,threads[0][0])).fetchall()
        gpu_work=c.execute("select count(*) from OPENGL_WORKLOAD a"+match+" where p.pid=?",(pid,)).fetchone()[0]
        thread_names=c.execute("select distinct s.value from ThreadNames t join StringIds s on s.id=t.nameId "
            "where (t.globalTid & 16777215)=?",(threads[0][0],)).fetchall()
        assert gpu_work>0 and ("Render thread",) in thread_names
        return dict(javaPid=pid,openGlEvents=n,gpuWorkloadEvents=gpu_work,renderThread=threads[0][0],
                    apiSpanMs=(e-b)/1e6,apiThreads=threads,
                    apiCalls=calls,osRuntimeOnTopGlThread=osrt,openGlTables=sorted(t for t in tables if t.startswith("OPENGL")))

def collect(label,runtime):
    output=WORK/label
    output.mkdir()
    before=lab_check()
    assert not inspect_gpu()["foreign"], "another job owns the renderer"
    env={k:os.environ[k] for k in ("HOME","USER","LOGNAME","PATH","LANG","XDG_RUNTIME_DIR","SHELL") if k in os.environ}
    name="aql"+uuid.uuid4().hex
    session=["--session="+name]
    started=False
    with tempfile.TemporaryDirectory(prefix="aql-nsight-") as tmp,(output/"collector.log").open("wb") as log:
        base=Path(tmp);game=base/"minecraft"
        folder=prepare(game)
        cache=ROOT/"build/gpu-profiler/driver-cache"
        runenv=dict(env,ALSOFT_DRIVERS="null",__GL_SHADER_DISK_CACHE_PATH=str(cache),XDG_CACHE_HOME=str(base/"cache"))
        private=base/"wayland"
        private.mkdir(mode=0o700)
        display_info=base/"display.json"
        # The private compositor starts its own Xwayland server. The child only publishes
        # its display address inside the fresh temporary directory and waits for shutdown.
        child=("import json,os,sys,time; from pathlib import Path; "
               "Path(sys.argv[1]).write_text(json.dumps({k:os.environ[k] for k in "
               "('DISPLAY','XAUTHORITY') if k in os.environ})); time.sleep(900)")
        compositor_env=dict(env,XDG_RUNTIME_DIR=str(private),WLR_HEADLESS_OUTPUTS="1",WLR_BACKENDS="headless",
            WLR_RENDERER="gles2",WLR_RENDER_DRM_DEVICE="/dev/dri/renderD128",
            LD_LIBRARY_PATH=str(runtime/"usr/lib/x86_64-linux-gnu"))
        compositor=subprocess.Popen([runtime/"usr/bin/cage","--",sys.executable,"-c",child,str(display_info)],
            env=compositor_env,cwd=base,stdout=log,stderr=log,start_new_session=True)
        for _ in range(120):
            if display_info.exists() and display_info.stat().st_size:break
            if compositor.poll() is not None:raise RuntimeError("Private compositor exited")
            time.sleep(.1)
        runenv.update(read(display_info))
        display=runenv["DISPLAY"]
        assert display and display!=os.environ.get("DISPLAY")
        rt=read(HERE.parent/"2026-11-20-underwater-refinement/local-launch.json")
        java=[rt["java"],"-Xms512m","-Xmx2600m","-XX:ActiveProcessorCount=4","-Dorg.lwjgl.openal.libname=libopenal.so.1","-cp",
            ":".join(rt["cp"]),"net.fabricmc.loader.impl.launch.knot.KnotClient","--username","Woodwalker","--version","1.21.1",
            "--gameDir",str(game),"--assetsDir",str(GAME.parents[2]/"assets"),"--assetIndex","17","--uuid","00000000000040008000000000000308",
            "--accessToken","0","--userType","legacy","--width","1600","--height","900","--quickPlaySingleplayer",folder]
        def cli(args,timeout=45,check=True):
            return subprocess.run(["nsys",*args],cwd=base,env=env,stdout=log,stderr=log,timeout=timeout,check=check)
        try:
            launch=subprocess.Popen(["nsys","launch","--session-new="+name,"--trace=opengl,osrt","--opengl-gpu-workload=true",
                "--osrt-threshold=50000",*java],cwd=game,env=runenv,stdout=log,stderr=log,start_new_session=True)
            started=True
            game_log=game/"logs/latest.log"
            deadline=time.monotonic()+600
            while time.monotonic()<deadline:
                txt=game_log.read_text(errors="replace") if game_log.exists() else ""
                if "Woodwalker joined the game" in txt and "worker threads" in txt.split("Woodwalker joined the game")[-1]:
                    break
                if launch.poll() not in (None,0) and not owned_java(game):raise RuntimeError(f"Nsight launcher exited {launch.returncode}")
                time.sleep(1)
            else:raise RuntimeError("No guarded world join before timeout")
            pid=owned_java(game)
            selected=next(line for line in txt.splitlines() if "OpenGL Renderer:" in line)
            assert pid and "RTX 3080 Ti" in selected and SHIP.name in txt
            time.sleep(5)
            assert owned_java(game)==pid
            windows=subprocess.check_output(["xdotool","search","--onlyvisible","--pid",str(pid),"--name","Minecraft"],env=runenv,text=True).split()
            assert len(windows)==1
            geom=subprocess.check_output(["xdotool","getwindowgeometry","--shell",windows[0]],env=runenv,text=True)
            dimensions={k:int(v) for k,v in (line.split("=",1) for line in geom.splitlines()) if k in ("WIDTH","HEIGHT")}
            cli(["start",*session,"--sample=none","--cpuctxsw=none","--output="+str(output/"minecraft")])
            time.sleep(6)
            cli(["stop",*session],timeout=100)
            (output/"client.log").write_text(game_log.read_text(errors="replace"))
        finally:
            pid_alive=owned_java(game)
            if pid_alive: os.kill(pid_alive,signal.SIGTERM)
            for _ in range(80):
                if not owned_java(game):break
                time.sleep(.25)
            if owned_java(game):os.kill(owned_java(game),signal.SIGKILL)
            if started:
                cli(["shutdown",*session],check=False)
                launch.wait(timeout=30)
            if compositor.poll() is None:os.killpg(compositor.pid,signal.SIGTERM)
            compositor.wait(timeout=15)
        report=output/"minecraft.nsys-rep"
        assert report.is_file() and report.stat().st_size>0
        subprocess.run(["nsys","export","--type=sqlite","--output="+str(output/"minecraft.sqlite"),str(report)],
            cwd=base,env=env,check=True,stdout=log,stderr=log)
        result=summarize(output/"minecraft.sqlite",pid)
        assert lab_check()==before
        result.update(renderer=selected,pack=SHIP_SHA,checkpoint=SAVE_SHA,
                      size=[dimensions["WIDTH"],dimensions["HEIGHT"]],backend="private headless Cage/Xwayland",requestedSeconds=6,labUnchanged=True,report=str(report.relative_to(ROOT)),reportSha256=sha(report))
        (HERE/(label+".json")).write_text(json.dumps(result,indent=2)+"\n")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("--cage-root",type=Path,required=True,help="Root containing usr/bin/cage and its Wayland libraries")
    args=parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*",args.label):
        parser.error("Use a fresh directory label made of lowercase letters, digits and hyphens")
    with open("/tmp/aql-render21-1000.lock","a+b") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        collect(args.label,args.cage_root.resolve(strict=True))
