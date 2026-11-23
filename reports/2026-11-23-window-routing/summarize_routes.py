"""Match real Minecraft frame ordinals and inspect the saved guard receipts."""
import json
from statistics import mean
from route_room import BEAM, HERE, ROOT, guarded, gpu
from selective_room import DIGEST, PACK
from profile_data import collect_window, read_rows

read=lambda p:json.loads(p.read_text())

def gpu_window(folder,pack,stage):
    assert read(folder/"summary.json")["packSha"]==guarded.sha(pack)
    ref=gpu.extract(folder,stage,None,pack_path=pack,condition=stage,min_frames=50)
    ids=gpu.window_ids((folder/"client.log").read_text(),stage,ref["intervalsUs"])
    with (guarded.BUILD/(folder.name+".csv")).open() as src: return collect_window(read_rows(src),ids)

def summarize():
    delta={}
    old=ROOT/"dist/Aqualumen-Sunlit-Panes.zip"
    cache=ROOT/"dist/Aqualumen-Window-Cells.zip"
    for forest,stages in ((False,("air","red-ew")),(True,("birch-0","birch-4"))):
        a="birch-" if forest else ""
        dirs={"base":(BEAM/("gp-window-"+a+"control-profile"),old),"cells":(BEAM/("gp-window-"+a+"cells-profile"),cache),
              "selective":(HERE/("gp-lit-route-"+("birch" if forest else "room")),PACK)}
        for stage in stages:
            rows={k:gpu_window(d,p,stage) for k,(d,p) in dirs.items()}
            n=min(map(len,rows.values()))
            assert n>=50
            data={}
            for k,points in rows.items():
                inc=[v["inclusive"] for v in points[:n]]
                def avg(*names):return mean(sum(r.get(name,0) for name in names) for r in inc)/1e6
                data[k]=dict(frame=avg("frame"),ordinaryDraw=avg("quad/deferred"),windowDraw=avg("quad/deferred1"),
                             combinedDraw=avg("quad/deferred","quad/deferred1"),compute=avg("dispatch/shadowcomp7","dispatch/shadowcomp8"))
            delta[stage]=dict(framesEach=n,meanGPUMs=data)
    intervals={}
    for role,files in {"base":[BEAM/"control-reverse",BEAM/"birch-control"],"cells":[BEAM/"cells-reverse",BEAM/"birch-cells"],
                       "first":[HERE/"route-room-r2",HERE/"route-birch"],"selective":[HERE/"selective-room",HERE/"selective-birch"]}.items():
        intervals[role]={s:{k:w[k] for k in ("cpuMeanMs","cpuP99Ms","frames")} for f in files for s,w in read(f/"summary.json")["scenes"].items()}
    receipts={}
    for f in sorted(HERE.glob("*/complete.json")):
        receipt=read(f)
        pf=read(f.parent/"preflight.json")
        assert pf["labBefore"]==pf["labAfter"] and not pf["foreignObservations"]
        if receipt["complete"]:
            assert "3080 Ti" in receipt["gl"]["renderer"] and receipt["shaderpackLogged"] and receipt["originalWorldAndConfigUnchanged"]
            assert receipt["packSha256"]==receipt["sourcePackShaNow"]
        receipts[f.parent.name]=dict(complete=receipt["complete"],timingAccepted=(f.parent/"summary.json").exists(),
                                     pack=receipt["packSha256"],failure=receipt["failure"])
    assert guarded.lab_check()==read(HERE/"selective-room/preflight.json")["labAfter"]
    dest=HERE/"comparison.json"
    dest.write_text(json.dumps(dict(sha256=DIGEST,ordinaryIntervals=intervals,profile=delta,receipts=receipts,
        normalLab=guarded.lab_check()["selected"]),indent=2)+"\n")
if __name__=="__main__":summarize()
