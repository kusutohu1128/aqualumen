"""Switch only the weather while recording the lantern reflection in a private client."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from room import HERE,CACHE,COMPILER,guarded
from packing import replace
from release import VERSION,SHA
from plane_result import SHIPPED_SHA

STEPS=("dry-start","rain-start","soaked","rain-stop","drying")
SWITCH={"rain-start":"rain","rain-stop":"clear"}


class WeatherRoom:
    def __init__(self,base):
        self.base=base
        for name in STEPS:
            base.STAGE_TABLE[name]=(True,True,None,"cobblestone",False,18000)

    def __getattr__(self,name):
        return getattr(self.base,name)

    def self_test(self,names):
        assert tuple(names)==STEPS

    def geometry(self,names):
        return dict(self.base.geometry(names),weatherSwitchTicks=120,sequence=list(STEPS))

    def datapack(self,names):
        files=self.base.datapack(names)
        files["data/animal/predicate/rain.json"]=json.dumps({"condition":"minecraft:weather_check","raining":True})
        prefix="data/animal/function/"
        for i,stage in enumerate(names):
            if stage in SWITCH:
                mode=SWITCH[stage]
                k=prefix+f"s{i}.mcfunction"
                files[k]=replace(files[k],f"say AQLAVA_BEGIN_{stage}_END",
                                 f"say AQLAVA_BEGIN_{stage}_END\nschedule function animal:weather_{mode} 120t replace")
                files[prefix+f"weather_{mode}.mcfunction"]=f"weather {mode} 1000000t\nsay AQ_WEATHER_SWITCH_{mode}_END\n"
            for phase in ("v","e"):
                rainy=stage=="soaked" or (stage=="rain-start" and phase=="e") or (stage=="rain-stop" and phase=="v")
                predicate=("if" if rainy else "unless")+" predicate animal:rain"
                k=prefix+f"{phase}{i}.mcfunction"
                files[k]=replace(files[k],"if block 406 152 -410 air",predicate+" if block 406 152 -410 air")
        return files


def window(game):
    # Select only the private JVM whose process arguments contain this game.
    for p in Path("/proc").glob("[0-9]*"):
        try:
            if (p/"comm").read_text().strip()!="java" or os.fsencode(game) not in (p/"cmdline").read_bytes().split(b"\0"):
                continue
            display=next(v[8:].decode() for v in (p/"environ").read_bytes().split(b"\0") if v.startswith(b"DISPLAY="))
        except (FileNotFoundError,PermissionError,ProcessLookupError):
            continue
        assert re.fullmatch(r":\d+",display) and int(display[1:])>=171
        env={k:v for k,v in os.environ.items() if k not in ("XAUTHORITY","WAYLAND_DISPLAY")}
        env["DISPLAY"]=display
        found=subprocess.check_output(["xdotool","search","--all","--onlyvisible","--pid",p.name,"--name","Minecraft"],env=env,text=True).split()
        assert len(found)==1
        return env,found[0],int(p.name)
    raise RuntimeError("private Minecraft window not found")


def run(label):
    assert label in ("reference","wet-plane")
    pack=VERSION if label=="reference" else VERSION.with_name("Aqualumen-Wet-Plane-Study.zip")
    assert guarded.sha(pack)==(SHA if label=="reference" else SHIPPED_SHA)
    stop=threading.Event()
    worker=None
    errors=[]
    def prepare(game,out,mods):
        nonlocal worker
        def capture():
            try:
                data={}
                log=game/"logs/latest.log"
                for stage,mode in SWITCH.items():
                    deadline=time.monotonic()+600
                    def wait_for(marker):
                        while not stop.is_set() and time.monotonic()<deadline:
                            if log.exists() and marker in log.read_text(errors="replace"):return time.monotonic()
                            time.sleep(.04)
                        raise TimeoutError(marker)
                    wait_for(f"AQLAVA_BEGIN_{stage}_END")
                    env,wid,pid=window(game)
                    started=time.monotonic()
                    stats=out/(mode+"-capture-progress.txt")
                    cmd=["ffmpeg","-hide_banner","-loglevel","error","-n","-stats_period","0.1","-progress",str(stats),"-f","x11grab",
                         "-framerate","30","-draw_mouse","0","-window_id",wid,"-i",env["DISPLAY"],"-t","11","-vf","crop=480:200:0:676",
                         "-threads","2","-c:v","ffv1","-pix_fmt","bgr0",str(out/(mode+"-floor.mkv"))]
                    with (out/(mode+"-recorder.log")).open("wb") as stderr:
                        process=subprocess.Popen(cmd,env=env,stderr=stderr)
                        try:
                            switch_at=wait_for("AQ_WEATHER_SWITCH_"+mode+"_END")-started
                            progress=stats.read_text() if stats.exists() else ""
                            recorded=re.findall(r"^frame=(\d+)",progress,re.M)
                            assert recorded and int(recorded[-1])>=65,(switch_at,recorded[-1:])
                            assert process.wait(timeout=20)==0
                        finally:
                            if process.poll() is None:
                                process.terminate();process.wait(timeout=6)
                    assert 2.5<switch_at<9
                    data[mode]=dict(privatePid=pid,display=env["DISPLAY"],window=wid,switchSecondsAfterRecorderStart=switch_at,
                                    lastMuxedFrameBeforeSwitch=int(recorded[-1]),cropXYWH=[0,676,480,200])
                    (out/"weather-capture.json").write_text(json.dumps(data,indent=2)+"\n")
            except Exception as exc:
                errors.append(str(exc))
        worker=threading.Thread(target=capture,daemon=True)
        worker.start()
    def collect(game,out):
        stop.set()
        worker.join(8)
        if errors or worker.is_alive():raise RuntimeError(errors)
        assert set(json.loads((out/"weather-capture.json").read_text()))=={"rain","clear"}
    fixed=dict(backend="vgl",size="1600x900",settle="1",glcache=str(CACHE),stages=",".join(STEPS),
               **{"period-ticks":"260","shot-gap":"0.15","compiler-mod":str(COMPILER)})
    guarded.launch(pack,"weather-cycle-"+label,"off",fixed,HERE,WeatherRoom,prepare,collect)


if __name__=="__main__":
    run(sys.argv[1])
