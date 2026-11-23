"""Read both paths for the very same moving cow, pixel, lamp and rendered frame."""
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORK=ROOT/"build/torch-cell-shadow"
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-shadow-integral"))
from animal_run import SteppedGrove, guarded

def replace(source,before,after):
    assert source.count(before)==1,before
    return source.replace(before,after)

def build():
    origin=WORK/"Aqualumen-Torch-Cell-Meter.zip"
    assert guarded.sha(origin)=="7cbf8e456ec5a2e9d812a74a5b8fb02b0063816e387fa6e53b0ea9f81e1b21e9"
    out=WORK/"Aqualumen-Torch-Cell-Moving-Meter.zip"
    with ZipFile(origin) as a,ZipFile(out,"w") as b:
        for ent in a.infolist():
            data=a.read(ent)
            if ent.filename=="shaders/shadowcomp6.csh":
                s=replace(data.decode(),"int flags=0;","int flags=0, added=0;")
                start="geometry=tight;"
                s=replace(s,start,start+"\n                if(tight==0) added|=1<<i;")
                s=replace(s,"flags|=(1<<i)|(1<<(i+12));","added|=1<<i;\n                    flags|=(1<<i)|(1<<(i+12));")
                store="imageStore(lampFieldImage,openCellAddress(cell),vec4(float(flags)));"
                data=replace(s,store,store+"\n        imageStore(lampFieldImage,openCellAddress(cell)+ivec2(0,12896),vec4(float(added)));").encode()
            if ent.filename=="shaders/shaders.properties":
                data=replace(data.decode(),"512 15008","512 15520").encode()
            if ent.filename=="shaders/lib/local_lighting.glsl":
                s=data.decode()
                i=s.index("        if(probeBaseline) {")
                j=s.index("        ivec3 cell=ivec3(floor(start));",i)
                assert s[i:j].count("} else {")==1
                s=s[:i]+s[j:]
                s=replace(s,"        }\n    }\n#endif\n    if(carried && !occluders.leafVolume)", "    }\n#endif\n    if(carried && !occluders.leafVolume)")
                target="        int flags=flagsForTorch(cell,centre,slot);"
                # The previous implementation had no record for either of the
                # newly proved cases. All other paths use the exact same flags.
                s=replace(s,target,target+"""
        if(probeBaseline && flags!=0 && (int(texelFetch(aqualumenLightField,openCellAddress(cell)+ivec2(0,12896),0).r)&(1<<slot))!=0) {
            probeAdded=true;
            flags=0;
        }""")
                s=replace(s,"bool probeBaseline=false;","bool probeBaseline=false,probeAdded=false;")
                s=replace(s,"        probeBaseline=true;","        probeAdded=false; probeBaseline=true;")
                s=replace(s,"int flags=64+probeMethod+","int flags=64+probeMethod+(probeAdded?32:0)+")
                data=s.encode()
            b.writestr(ent,data)
    return out

class Moving(SteppedGrove):
    def self_test(self,names):
        assert names==["walk","walk-cleared"]

class MovingGlass(Moving):
    # The glass hangs two cells above the floor torch, clear of the cow.
    # Its cell falls inside many bounding boxes but outside the actual light beam.
    def geometry(self,names):
        return dict(super().geometry(names),overheadGlass=[405,153,-408])

    def datapack(self,names):
        files=super().datapack(names)
        for i,name in enumerate(names):
            key=f"data/animal/function/s{i}.mcfunction"
            marker=f"say AQLAVA_BEGIN_{name}_END"
            files[key]=replace(files[key],marker,"setblock 405 153 -408 white_stained_glass\n"+marker)
            for stage in ("v","e"):
                key=f"data/animal/function/{stage}{i}.mcfunction"
                check="if block 405 151 -408 torch"
                files[key]=replace(files[key],check,check+" if block 405 153 -408 white_stained_glass")
        return files

class Recorder:
    def __init__(self, marker="AQ_WALK_START", movie="cow-motion.mkv", duration=11):
        self.marker=marker
        self.movie=movie
        self.duration=duration
        self.stop=threading.Event()
        self.error=None

    def prepare(self,game,out,mods):
        self.thread=threading.Thread(target=self.record,args=(game,out),daemon=True)
        self.thread.start()

    def record(self,game,out):
        try:
            while not self.stop.wait(.05):
                log=out/"client.log"
                if log.exists() and self.marker in log.read_text(errors="replace"): break
            else: return
            lines=(out.parent/"progress.txt").read_text().splitlines()
            match=next(re.search(r"display=(:\d+)",s) for s in reversed(lines)
                       if f"game={game} " in s and "display=" in s)
            display=match.group(1)
            env=dict(os.environ,DISPLAY=display)
            ids=subprocess.check_output(["xdotool","search","--onlyvisible","--name","Minecraft"],env=env,text=True).split()
            owned=[]
            for window in ids:
                pid=subprocess.check_output(["xdotool","getwindowpid",window],env=env,text=True).strip()
                if (Path("/proc")/pid/"cwd").resolve()==game.resolve(): owned.append(window)
            assert len(owned)==1 and int(display[1:])>=231,(owned,display)
            with (out/("capture.log" if self.movie=="cow-motion.mkv" else self.movie+".log")).open("xb") as log:
                subprocess.run(["ffmpeg","-v","error","-n","-f","x11grab","-draw_mouse","0","-framerate","12",
                    "-window_id",owned[0],"-i",display,"-t",str(self.duration),"-c:v","ffv1","-threads","2","-pix_fmt","bgr0",
                    out/self.movie],stdout=log,stderr=log,env=env,timeout=22,check=True)
        except Exception as e:
            self.error=e

    def collect(self,game,out):
        self.thread.join(timeout=23)
        self.stop.set()
        if self.error: raise self.error
        assert not self.thread.is_alive() and (out/self.movie).stat().st_size>1000

if __name__=="__main__":
    pack=build()
    if sys.argv[1:]==["--build"]: print(guarded.sha(pack)); sys.exit(0)
    label=sys.argv[1]
    assert not (HERE/label).exists()
    rec=Recorder()
    params=dict(backend="vgl",size="1280x720",settle="1",stages="walk,walk-cleared",glcache=str(guarded.BUILD/"driver-cache"),
                **{"period-ticks":"200","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    scene={"cow-motion":Moving,"glass-cow-motion":MovingGlass}[label]
    guarded.launch(pack,label,"off",params,HERE,scene,rec.prepare,rec.collect)
