"""Capture a short Nsight Systems trace in a new, private copy of the verified night trail."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess as sp
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OAK=HERE.parent/"2026-11-21-animal-light/woodland/oak-night-trail"
sys.path.insert(0,str(HERE.parent/"2026-11-22-gpu-profile"))
from run import lab_check, inspect_gpu, GAME


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(output, cage_root):
    output.mkdir(mode=0o700,exist_ok=False,parents=True)
    record=json.loads((OAK/"complete.json").read_text())
    checkpoint=json.loads((OAK/"save.json").read_text())
    source=Path(record["privateGameDir"]).resolve()
    old_world=Path(json.loads((OAK/"identity.json").read_text())["world"]).resolve()
    assert source.parent.parent==Path("/tmp") and old_world.parent==source/"saves"
    assert record["cleanExit"] and record["packSha256"]=="a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9"
    assert sha(ROOT/checkpoint["archive"])==checkpoint["sha256"]
    before=lab_check()
    assert before==json.loads((HERE/"lab.json").read_text())["labAfter"]
    with open("/tmp/aql-render21-1000.lock","a+b") as lock, tempfile.TemporaryDirectory(prefix="aql-nsys-night-") as tmp:
        fcntl.flock(lock,fcntl.LOCK_EX)
        assert not inspect_gpu()["foreign"]
        work=Path(tmp)
        game=work/"minecraft"
        game.mkdir()
        for sub in ("mods","config","shaderpacks"):
            (game/sub).mkdir()
        shutil.copyfile(source/"options.txt",game/"options.txt")
        for name in record["mods"]:
            origin=source/"mods"/name
            expected=ROOT/"dist"/name if "lighting-compiler" in name else GAME/"mods"/name
            assert sha(origin)==sha(expected)
            shutil.copyfile(origin,game/"mods"/name)
        for name in ("iris.properties","sodium-options.json"):
            shutil.copyfile(source/"config"/name,game/"config"/name)
        pack=source/"shaderpacks"/record["pack"]
        assert sha(pack)==record["packSha256"]
        shutil.copyfile(pack,game/"shaderpacks"/pack.name)
        world=game/"saves"/checkpoint["folder"]
        for entry,digest in checkpoint["members"].items():
            src=old_world/entry
            assert src.resolve().is_relative_to(old_world) and sha(src)==digest
            dst=world/entry
            dst.parent.mkdir(exist_ok=True,parents=True)
            shutil.copyfile(src,dst)
        assert not (old_world/"datapacks").exists() or not any((old_world/"datapacks").iterdir())
        (world/"datapacks").mkdir(exist_ok=True)
        runtime=json.loads((HERE.parent/"2026-11-20-underwater-refinement/local-launch.json").read_text())
        client=[runtime["java"],"-Xms512m","-Xmx2600m","-XX:ActiveProcessorCount=4","-cp",":".join(runtime["cp"]),
                "net.fabricmc.loader.impl.launch.knot.KnotClient","--username","Woodwalker","--version","1.21.1",
                "--gameDir",str(game),"--assetsDir",str(GAME.parents[2]/"assets"),"--assetIndex","17",
                "--uuid","00000000000040008000000000000308","--accessToken","0","--userType","legacy",
                "--width","1600","--height","900","--quickPlaySingleplayer",world.name]
        cache=ROOT/"build/animal-light/woodland/driver-cache"/record["packSha256"][:16]
        # A native Xwayland context can need new driver binaries even with the VirtualGL cache populated.
        native_cache=ROOT/"build/torch-density/nsight-driver-cache"
        if not native_cache.exists():
            with tempfile.TemporaryDirectory(dir=native_cache.parent) as stage:
                shutil.copytree(cache,Path(stage)/"cache")
                (Path(stage)/"cache").rename(native_cache)
        env={k:os.environ[k] for k in ("PATH","HOME","USER","LANG","XDG_RUNTIME_DIR") if k in os.environ}
        private_runtime=work/"xdg-runtime"
        private_runtime.mkdir(mode=0o700)
        env.update(XDG_RUNTIME_DIR=str(private_runtime),WLR_BACKENDS="headless",WLR_RENDERER="gles2",
                   WLR_RENDER_DRM_DEVICE="/dev/dri/renderD128",WLR_HEADLESS_OUTPUTS="1",GBM_BACKEND="nvidia-drm",
                   __GLX_VENDOR_LIBRARY_NAME="nvidia",ALSOFT_DRIVERS="null",
                   __GL_SHADER_DISK_CACHE_PATH=str(native_cache),XDG_CACHE_HOME=str(work/"xdg"))
        cage="cage"
        if cage_root:
            env["LD_LIBRARY_PATH"]=str(cage_root/"usr/lib/x86_64-linux-gnu")
            cage=str(cage_root/"usr/bin/cage")
        ready=work/"surface.json"
        # Capture only display coordinates of the private compositor; all window operations below are PID-guarded.
        ready_command=("import os,json,sys,signal; from pathlib import Path; "
                       "Path(sys.argv[1]).write_text(json.dumps({k:os.environ[k] for k in "
                       "('DISPLAY','XAUTHORITY') if k in os.environ}));signal.pause()")
        with (output/"display.log").open("xb") as log:
            compositor=sp.Popen([cage,"-d","--",sys.executable,"-c",ready_command,str(ready)],env=env,
                                cwd=work,stdout=log,stderr=sp.STDOUT,start_new_session=True)
        try:
            until=time.monotonic()+10
            while not ready.exists():
                assert compositor.poll() is None and time.monotonic()<until,"private compositor startup"
                time.sleep(.05)
            coords=json.loads(ready.read_text())
            assert coords["DISPLAY"].startswith(":") and coords["DISPLAY"]!=os.environ.get("DISPLAY")
            env.update(coords)
            # Launch under Nsight. The report's process-environment table is kept in the private raw directory.
            session="AqlNight"+work.name.rsplit("-",1)[-1]
            cmd=["nsys","launch","--session-new="+session,"--trace=opengl,osrt","--opengl-gpu-workload=false",
                 "--osrt-threshold=1000000",*client]
            with (output/"collector.log").open("xb") as log:
                launcher=sp.Popen(cmd,env=env,cwd=game,stdout=log,stderr=sp.STDOUT)
                pid=None
                window=None
                started=False
                try:
                    deadline=time.monotonic()+600
                    while time.monotonic()<deadline:
                        game_log=game/"logs/latest.log"
                        if game_log.exists() and "contact bridge initialized" in game_log.read_text(errors="replace"):
                            break
                        if game_log.exists() and "Backend library:" in game_log.read_text(errors="replace"):
                            sessions=sp.check_output(["nsys","sessions","list"],text=True)
                            if session not in sessions:
                                raise RuntimeError("private Minecraft exited during graphics startup; see collector.log")
                        time.sleep(.4)
                    else: raise RuntimeError("private shader pipeline did not become ready")
                    txt=game_log.read_text(errors="replace")
                    assert "OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" in txt and "Using shaderpack: "+pack.name in txt
                    for proc in Path("/proc").glob("[0-9]*"):
                        try:
                            if (proc/"cwd").resolve()==game and (proc/"comm").read_text().strip()=="java":
                                args=(proc/"cmdline").read_bytes().split(b"\0")
                                if b"--gameDir" in args and args[args.index(b"--gameDir")+1]==os.fsencode(game):
                                    pid=int(proc.name);break
                        except (OSError,RuntimeError,ValueError):
                            continue
                    assert pid and pid!=os.getpid()
                    ids=sp.check_output(["xdotool","search","--onlyvisible","--pid",str(pid),"--name","Minecraft"],env=env,text=True).split()
                    assert len(ids)==1
                    window=ids[0]
                    geometry=sp.check_output(["xdotool","getwindowgeometry","--shell",window],env=env,text=True)
                    dimensions=dict(line.split("=",1) for line in geometry.splitlines())
                    time.sleep(3)
                    sp.run(["nsys","start","--session="+session,"--sample=none","--cpuctxsw=none","-o",str(output/"night")],
                           cwd=game,stdout=log,stderr=sp.STDOUT,check=True,timeout=60)
                    started=True
                    begin=time.monotonic()
                    time.sleep(5)
                    duration=time.monotonic()-begin
                    sp.run(["nsys","stop","--session="+session],cwd=game,stdout=log,stderr=sp.STDOUT,check=True,timeout=120)
                    started=False
                finally:
                    if started:
                        sp.run(["nsys","stop","--session="+session],stdout=log,stderr=sp.STDOUT,timeout=60)
                    if pid and window and Path("/proc",str(pid),"cwd").resolve()==game:
                        assert sp.check_output(["xdotool","getwindowpid",window],env=env,text=True).strip()==str(pid)
                        sp.run(["/tmp/aqualumen-wm-close",hex(int(window))],env=env,check=True,timeout=8)
                        for _ in range(100):
                            if not Path("/proc",str(pid)).exists(): break
                            time.sleep(.25)
                    sp.run(["nsys","shutdown","--session="+session,"--kill=sigterm"],stdout=log,stderr=sp.STDOUT,timeout=40)
                    launcher.wait(timeout=15)
            final=game_log.read_text(errors="replace")
            assert "All dimensions are saved" in final
            assert lab_check()==before and all(sha(old_world/e)==h for e,h in checkpoint["members"].items())
            sp.run(["nsys","export","--type=sqlite","--output="+str(output/"night.sqlite"),str(output/"night.nsys-rep")],check=True)
            return dict(javaPid=pid,report=str(output/"night.nsys-rep"),sqlite=str(output/"night.sqlite"),
                        windowSize=[int(dimensions["WIDTH"]),int(dimensions["HEIGHT"])],renderer=record["renderer"],packSha256=sha(pack),checkpointSha256=checkpoint["sha256"],
                        captureSeconds=duration,originalLabUnchanged=True,sourceSaveUnchanged=True,cleanExit=True)
        finally:
            import signal
            if compositor.poll() is None:
                os.killpg(compositor.pid,signal.SIGTERM)
                compositor.wait(timeout=10)


if __name__=="__main__":
    output=Path(sys.argv[1]).resolve()
    result=capture(output, Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None)
    (output/"receipt.json").write_text(json.dumps(result,indent=2)+"\n")
