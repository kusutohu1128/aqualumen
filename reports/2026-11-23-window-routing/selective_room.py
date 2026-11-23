"""Count only actual certified pane/torch paths. Include an unlit and a distant window."""
from route_room import ROOT, HERE, ChallengeRoom, guarded, TorchCounts, analyze, gpu
from window_room import LAYOUT

PACK=ROOT/"build/window-routing/selective/Aqualumen-Window-Routing.zip"
DIGEST="4ad4d044c9b39b30929fbaa1d0878e42d10224a240243165ade74e8e6acda5e7"
LAYOUT["unlit-pane"]=dict(LAYOUT["red-ew"])
LAYOUT["distant-pane"]={}

class SelectiveRoom(ChallengeRoom):
    def geometry(self,names):
        return dict(super().geometry(names), distantPane=[431,151,-407], unlitStage="unlit-pane")
    def datapack(self,names):
        files=super().datapack(names)
        for i,stage in enumerate(names):
            for phase in "sve":
                path=f"data/animal/function/{phase}{i}.mcfunction"
                text=files[path]
                if stage=="unlit-pane":
                    assert "405 151 -408 torch" in text
                    text=text.replace("405 151 -408 torch","405 151 -408 air")
                remote="red_stained_glass_pane" if stage=="distant-pane" else "air"
                if phase=="s":
                    marker=f"say AQLAVA_BEGIN_{stage}_END"
                    assert text.count(marker)==1
                    text=text.replace(marker, f"setblock 431 151 -407 {remote}\n"+marker)
                else:
                    marker="if block 405 151 -408 "
                    assert text.count(marker)==1
                    text=text.replace(marker, f"if block 431 151 -407 {remote} "+marker)
                files[path]=text
        return files

def run(label,forest=False,profile=False,reverse=False):
    assert guarded.sha(PACK)==DIGEST and not (HERE/label).exists()
    if profile: assert label.startswith("gp-")
    stages=["birch-0","birch-4"] if forest else ["air","red-ew","distant-pane","unlit-pane"]
    if reverse: stages.reverse()
    fixed=dict(backend="vgl",size="2560x1440",settle="1",stages=",".join(stages),glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"700" if profile else ("620" if forest else "550"),"shot-gap":".15",
                  "compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try: guarded.launch(PACK,label,"on" if profile else "off",fixed,HERE,TorchCounts if forest else SelectiveRoom)
    except SystemExit as exc:
        if exc.code: raise
    required=gpu.EXPECTED|{"dispatch/shadowcomp"+str(n) for n in (5,6,7,8)}|{"quad/deferred1"}
    analyze(HERE/label,PACK,profile,min_frames=50,required_passes=required)

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("label")
    for f in ("forest","profile","reverse"):p.add_argument("--"+f,action="store_true")
    a=p.parse_args()
    run(a.label,a.forest,a.profile,a.reverse)
