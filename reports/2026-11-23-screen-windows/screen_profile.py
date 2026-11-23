"""Profile both diffuse draws and their screen classifier on matching frame ordinals."""
import sys,json
from statistics import mean
from screen_trials import HERE,ROOT,PACK,DIGEST,guarded,SelectiveRoom,gpu,analyze
from summarize_routes import gpu_window

def run(label):
    assert label.startswith("gp-") and guarded.sha(PACK)==DIGEST and not (HERE/label).exists()
    stages=["red-ew","air"]
    fixed=dict(backend="vgl",size="2560x1440",settle="1",stages=",".join(stages),glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"700","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:guarded.launch(PACK,label,"on",fixed,HERE,SelectiveRoom)
    except SystemExit as exc:
        if exc.code:raise
    required=gpu.EXPECTED|{"dispatch/shadowcomp"+str(i) for i in (5,6,7,8)}|{"dispatch/deferred","quad/deferred1"}
    analyze(HERE/label,PACK,True,min_frames=50,required_passes=required)
    result={}
    for s in stages:
        data=gpu_window(HERE/label,PACK,s)
        result[s]={k:mean(r["inclusive"][k] for r in data)/1e6 for k in ("frame","dispatch/deferred","quad/deferred","quad/deferred1")}
        result[s]["frames"]=len(data)
    (HERE/label/"draws.json").write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__":run(sys.argv[1])
