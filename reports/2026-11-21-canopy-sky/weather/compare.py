"""Build comparison.jpg + summary.json from two completed weather runs (read-only on captures)."""
import json, subprocess, sys
from pathlib import Path
here = Path(__file__).resolve().parent
base, cand = here/"baseline-preview3", here/"candidate-c2"
scenes = [("ground-noon","overcast rain, world time 9800"),("ground-evening","clear dusk, world time 12400"),("ground-low-sun","rain dusk, world time 12400")]
FONT="/usr/share/fonts/opentype/fira/FiraMono-Medium.otf"
def load(d):
    t=json.loads((d/"timing.json").read_text()); r=json.loads((d/"capture/run.json").read_text())
    return t,r
res={}
for k,d in (("baseline",base),("candidate",cand)):
    t,r=load(d)
    res[k]={"pack":t["pack"],"sha256":t["sha256"],"renderer":t["renderer"],"framebuffer":t["framebuffer"],"samples":t["samples"],
            "compilerModSha256":t["compilerModSha256"],"worldAndConfigUnchanged":t["worldAndConfigUnchanged"],
            "complete":json.loads((d/"capture/complete.json").read_text())["status"],
            "scenes":{}}
    for s,_ in scenes:
        j=json.loads((d/"capture"/(s+".json")).read_text())
        res[k]["scenes"][s]={x:j[x] for x in j if x in("frames","mean_fps","p99_ms","framebuffer_resolution","requested_world_time","camera_follows_local_player")}
        res[k]["scenes"][s]["png"]=str((d/"capture"/(s+".png")).relative_to(here))
inputs=[];flt=[];labels=[]
for i,(s,desc) in enumerate(scenes):
    for j,(k,d) in enumerate((("baseline preview3",base),("candidate c2",cand))):
        n=i*2+j; inputs+=["-i",str(d/"capture"/(s+".png"))]
        flt.append(f"[{n}:v]scale=960:-1,drawtext=fontfile={FONT}:text='{k} | {desc}':x=8:y=8:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.6[v{n}]")
chain="".join(f"[v{n}]" for n in range(6))
flt.append(f"{chain}xstack=inputs=6:layout=0_0|960_0|0_540|960_540|0_1080|960_1080[o]")
out=here/"comparison.jpg"
subprocess.run(["ffmpeg","-v","error","-n",*inputs,"-filter_complex",";".join(flt),"-map","[o]","-frames:v","1","-q:v","3",str(out)],check=True)
res["comparison"]=str(out.relative_to(here))
(here/"summary.json").write_text(json.dumps(res,indent=2)+"\n")
