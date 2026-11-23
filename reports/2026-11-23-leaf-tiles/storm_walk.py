"""Play the normal preview under a wet oak at midnight in a disposable checkpoint copy."""
import gzip
import math
from pathlib import Path
import struct
import subprocess
import time

def set_rain(level, expected_time=68853):
    from mcnbt import parse
    raw=gzip.decompress(level.read_bytes())
    expected=parse(raw);data=expected["Data"]
    assert data["WorldGenSettings"]["seed"]==308060 and data["Time"]==data["DayTime"]==expected_time
    assert data["GameRules"]["doDaylightCycle"]==data["GameRules"]["doWeatherCycle"]=="false"
    assert data["raining"]==data["clearWeatherTime"]==data["thundering"]==0
    midnight=expected_time//24000*24000+18000
    for name,tag,fmt,value in (("DayTime",4,">q",midnight),("raining",1,">b",1)):
        header=bytes((tag,))+struct.pack(">H",len(name))+name.encode()
        old=header+struct.pack(fmt,data[name]);new=header+struct.pack(fmt,value)
        assert raw.count(old)==1
        raw=raw.replace(old,new);data[name]=value
    assert parse(raw)==expected
    level.write_bytes(gzip.compress(raw,mtime=0))
    return dict(dayTime=data["DayTime"],rain=1,weatherCycle=False,daylightCycle=False)


def walk(world,first,results,trail,turn,goto,observe,f3,key,hold,shot,hotbar,display,wid,env,out,tracking=False):
    trail.build("oak-night-trail",world,first["xyz"],destination=(569,64,419))
    start=(565.592,64.,419.493)
    assert trail.clear_line((565,64,419),(570,64,419))
    counts=[sum(trail.name(x,y,419).endswith("_leaves") for y in range(66,77)) for x in range(565,571)]
    assert counts[0]==0 and min(counts[1:])>=2
    assert hotbar()["2"]=="minecraft:torch" and hotbar()["3"]=="minecraft:soul_torch"
    results["leafBlocksOverPath"]=counts
    crossings=(("warm-track","2"),("empty-track","1")) if tracking else (("warm","2"),("soul","3"),("empty","1"))
    for label,slot in crossings:
        key(slot);o=goto(start,label+"-start",.12)
        for _ in range(5):
            turn(-90.,18.,o)
            o=observe(label+"-before")
            if abs(o["angle"][0]+90)<.4 and abs(o["angle"][1]-18)<.5:
                break
        else:
            raise AssertionError(f"{label}: camera did not reach the requested view, {o['angle']}")
        before=o
        tracked=tracking
        shot(label+"-outside",1.2,f2=True);f3(tracked)
        path=Path(out)/(label+"-crossing"+(".mkv" if tracked else ".mp4"))
        codec=(["-c:v","ffv1","-threads","3","-pix_fmt","bgr0"] if tracked else
               ["-c:v","libx264","-preset","veryfast","-threads","3","-crf","16","-pix_fmt","yuv420p","-movflags","+faststart"])
        with (Path(out)/(label+"-ffmpeg.log")).open("xb") as log:
            with subprocess.Popen(["ffmpeg","-hide_banner","-loglevel","error","-n","-f","x11grab","-framerate","24",
                      "-window_id",str(wid),"-i",display,*codec,str(path)],
                      env=env,stdin=subprocess.PIPE,stdout=log,stderr=log) as video:
                try:
                    time.sleep(.85);hold("w",1.15);time.sleep(.65)
                finally:
                    if video.poll() is None:
                        video.stdin.write(b"q\n");video.stdin.flush()
                    assert video.wait(timeout=20)==0
        after=observe(label+"-after")
        assert before["xyz"][0]<567.5<568.5<after["xyz"][0]<571.5
        assert abs(after["xyz"][2]-before["xyz"][2])<.12 and math.dist(before["angle"],after["angle"])<.3
        shot(label+"-under-oak",1.3,f2=True)
        results.setdefault("stormCrossings",[]).append(dict(light=label,before=before,after=after,video=path.name))
