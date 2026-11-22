"""Join GPU submission ordinals to the historical READY/F2/STILL CPU window."""
import argparse
from datetime import datetime
from collections import Counter
import csv
import json
from pathlib import Path
import re
from statistics import mean
import subprocess
import sys

from profile_data import calibration, collect_window, overhead, percentile, read_rows
from run import BUILD, ORDER, PACKS, R, ROOT, RUNS, T, save, sha, latest, run_base

sys.path.insert(0,str(T/"timing"))
from measure import extract

SCENES=("both-west","day-white")
HEADER=("epoch","frame","range","start_ns","end_ns","parent","draws","empty_slots","scene","cpu_interval_us")
EXPECTED={"dispatch/"+name for name in ("begin","begin1","prepare2","prepare3","prepare4","shadowcomp",
          "shadowcomp1","shadowcomp2","shadowcomp3","shadowcomp4","composite3")}
EXPECTED.update("quad/"+name for name in ("prepare","prepare1","deferred","composite","composite1","composite2","final"))


def read(path):
    return json.loads(path.read_text())


def window_ids(log, scene, reference):
    start=log.index("[Server] AQLAVA_READY_"+scene+"_END")
    end=log.index("[Server] AQLAVA_STILL_"+scene+"_END",start)
    text=log[log.index(".pngとして保存しました",start,end):end]
    pairs=re.findall(r"AQ_RENDER_FRAME_END (\d+) (\d+)",text)
    ends={int(stamp):int(n) for stamp,n in pairs}
    if len(ends)!=len(pairs):
        raise ValueError("duplicate CPU batch timestamp")
    stamps=re.findall(r"AQ_RENDER_INTERVALS_US (\d+) ([\d ]+)",text)
    ids, intervals=[],[]
    for stamp,values in stamps[3:]:
        us=list(map(int,values.split()))
        tail=ends[int(stamp)]
        ids.extend(range(tail-len(us)+1,tail+1))
        intervals.extend(us)
    n=len(reference)
    if intervals[:n]!=reference or ids[:n]!=list(range(ids[0],ids[0]+n)):
        raise ValueError("CPU window ordinal mismatch")
    return ids[:n]


def distribution(values):
    return {"medianMs":percentile(values,.5)/1e6,"p95Ms":percentile(values,.95)/1e6}


def gpu_stats(samples):
    names=sorted({name for f in samples for name in f["inclusive"]})
    total=sum(f["inclusive"]["frame"] for f in samples)
    stats={}
    for name in names:
        durations=[f["inclusive"].get(name,0) for f in samples]
        conditional=[f["inclusive"][name] for f in samples if name in f["inclusive"]]
        stats[name]={**distribution(durations),"exclusive":distribution([f["exclusive"].get(name,0) for f in samples]),
                     "whenExecuted":distribution(conditional),"framesExecuted":len(conditional),
                     "calls":sum(f["calls"].get(name,0) for f in samples),
                     "draws":sum(f["draws"].get(name,0) for f in samples)}
    residual=[f["residual"] for f in samples]
    return {"frames":len(samples),"ranges":stats,"residual":distribution(residual),
            "uncoveredPercent":100*sum(residual)/total,"maxErrorMs":max(f["error"] for f in samples)/1e6}


def startup(label, log):
    line,=[line for line in (RUNS/"progress.txt").read_text().splitlines()
           if f" {label}: 起動 backend=" in line]
    launch=datetime.fromisoformat(line.split()[0])
    pipeline=log.index("Creating pipeline for dimension minecraft:overworld")
    workers=re.search(r"\[([\d:]+)\] \[Render thread/INFO\]: Started [1-9]\d* worker threads",log[pipeline:])
    first=re.search(r"AQ_RENDER_INTERVALS_US (\d+) ([\d ]+)",log[pipeline+workers.end():])
    stamp=int(first[1])/1000
    return {"launch":launch.isoformat(),"workerStarted":workers[1],
            "launchToFirstPostWorkerBatchSeconds":round(stamp-launch.timestamp(),3)}


def summarize(label):
    base=run_base(label)
    folder=RUNS/label
    receipt=read(folder/"complete.json")
    pre=read(folder/"preflight.json")
    observer=read(folder/"observer.json")
    log=(folder/"client.log").read_text()
    assert "AQ_PROFILE_INVALID" not in log
    arm=ORDER[base]
    packname,digest=PACKS[arm]
    pack=(BUILD if arm=="cal" else ROOT/"dist")/packname
    historical=read(T/"ceiling-isolated/complete.json")
    assert receipt["packSha256"]==receipt["sourcePackShaNow"]==sha(pack)==digest
    assert receipt["compilerModSha256"]==historical["compilerModSha256"]
    assert receipt["sourceDigest"]==historical["sourceDigest"] and read(folder/"geometry.json")==read(T/"ceiling-isolated/geometry.json")
    assert receipt["gl"]["renderer"]==historical["gl"]["renderer"] and receipt["shaderpackLogged"] and receipt["complete"]
    assert not pre["foreignObservations"] and pre["labBefore"]==pre["labAfter"] and pre["samples"]>0
    assert observer["worldId"]=="b22dbccb-2970-41e6-847f-f183b1ec923d" and observer["frameObserverSha256"]==sha(BUILD/"frame-sample.jar")
    enabled="-off-" not in base
    hooks=re.findall(r"AQ_PROFILE_HOOK [^\n]+",log)
    stamps=[(s,extract(folder,s,None,pack_path=pack)["intervalsUs"]) for s in SCENES]
    result={"label":label,"pack":packname,"sha256":digest,"hooks":hooks,"enabled":enabled,"scenes":{}}
    result.update(startup=startup(label,log), profiledJar=observer.get("gpuProfilerSha256"),
                  cachePopulatedBefore=pre["cacheBefore"]["populated"],renderer=receipt["gl"],
                  cacheFilesBefore=pre["cacheFilesBefore"],worldUnchanged=receipt["originalWorldAndConfigUnchanged"],
                  labMetadata=pre["labAfter"]["metadata"])
    frames={}
    if enabled:
        assert observer["gpuProfilerSha256"]==sha(BUILD/"gpu-profiler.jar")
        assert Counter(hooks)==Counter((BUILD/"injections.txt").read_text().splitlines())
        assert "AQ_PROFILE_STATE bindings preserved" in log and re.search(r"AQ_PROFILE_READY bits=\d+ renderer=NVIDIA GeForce RTX 3080 Ti",log)
        raw=BUILD/(label+".csv")
        with (raw if raw.exists() else folder/"frames.csv").open() as f:
            frames=read_rows(f)
    else:
        assert not hooks and "gpuProfilerSha256" not in observer and not (BUILD/(label+".csv")).exists()
    result["slotInventory"]=re.findall(r"AQ_PROFILE_SLOT ([^\n]+)",log)
    result["sessionDrops"]=re.findall(r"AQ_PROFILE_DROP ([^\n]+)",log)
    out=[]
    for scene,us in stamps:
        ids=window_ids(log,scene,us)
        data={"firstId":ids[0],"lastId":ids[-1],"intervalsUs":us,"meanMs":mean(us)/1000,
              "fps":1e6/mean(us),"p95Ms":percentile(us,.95)/1000,"p99Ms":percentile(us,.99)/1000}
        if enabled:
            samples=collect_window(frames,ids)
            data["gpu"]=gpu_stats(samples)
            required=set(EXPECTED)
            if arm=="cal": required.update(f"dispatch/shadowcomp{n}" for n in (5,6,7))
            for f in samples:
                actual={k for k in f["calls"] if k.startswith(("quad/","dispatch/"))}
                if actual!=required or any(f["calls"][k]!=1 or f["draws"][k]!=1 for k in required):
                    raise ValueError(f"program inventory {actual ^ required} in {scene}")
            epoch,=set(e for e,n in frames if n==ids[0])
            empty=Counter()
            for n,interval in zip(ids,us):
                for row in frames[epoch,n]:
                    if row[5]:
                        empty[(row[0],row[5])]+=1
                out.extend((epoch,n,*row,scene,interval) for row in frames[epoch,n])
            data["emptySlotGroups"]=[{"stage":stage,"indices":indices,"frames":count}
                                     for (stage,indices),count in sorted(empty.items())]
            if arm=="cal":
                data["repeatedMs"]=percentile([sum(f["inclusive"][f"dispatch/shadowcomp{n}"] for n in (4,5,6,7)) for f in samples],.5)/1e6
        result["scenes"][scene]=data
    with (folder/("frames.csv" if enabled else "intervals.csv")).open("w") as stream:
        writer=csv.writer(stream,lineterminator="\n")
        if enabled:
            writer.writerow(HEADER); writer.writerows(out)
        else:
            writer.writerow(["frame","scene","cpu_interval_us"])
            for scene,d in result["scenes"].items():
                writer.writerows((d["firstId"]+i,scene,v) for i,v in enumerate(d["intervalsUs"]))
    result["validated"]=True
    save(folder/"summary.json",result)
    return result


def roi(label):
    # On the 1440p both-west F2 this 21x21 window lies inside the static ceiling, above the cow.
    data=subprocess.check_output(["ffmpeg","-v","error","-i",str(RUNS/label/"both-west-ingame.png"),"-vf",
        "crop=21:21:1270:70,format=rgb24","-frames:v","1","-f","rawvideo","-"])
    assert len(data)==21*21*3
    return [mean(data[i::3]) for i in range(3)]


def gates(early=False):
    runs={k:read(RUNS/latest(k)/"summary.json") for k in (list(ORDER)[:3] if early else ORDER)}
    assert all(r["validated"] for r in runs.values())
    assert len({r["profiledJar"] for r in runs.values() if r["enabled"]})==1
    assert len({r["labMetadata"] for r in runs.values()})==1
    cal,base=runs["gp-cal-4x-c"],runs["gp-p7-a"]
    scene="both-west"
    x,y=cal["scenes"][scene],base["scenes"][scene]
    rgbs=[roi(r["label"]) for r in (cal,base)]
    controls=lambda d: [d["gpu"]["ranges"][key]["medianMs"] for key in ("dispatch/prepare2","quad/final")]
    control=calibration(x["repeatedMs"],y["gpu"]["ranges"]["dispatch/shadowcomp4"]["medianMs"],
                        controls(x),controls(y),max(abs(a-b) for a,b in zip(*rgbs)))
    control.update(repeatedMs=x["repeatedMs"],singleMs=y["gpu"]["ranges"]["dispatch/shadowcomp4"]["medianMs"],roiMeanRGB=rgbs)
    overheads={}
    for pair in ("a",) if early else ("a","b"):
        off,on=runs["gp-overhead-off-"+pair],runs["gp-p7-"+pair]
        overheads[pair]={s:overhead(off["scenes"][s]["intervalsUs"],on["scenes"][s]["intervalsUs"]) for s in SCENES}
    passed=control["pass"] and all(v["pass"] for pair in overheads.values() for v in pair.values())
    result={"status":("early-gates-passed" if early else "completed") if passed else "stopped-at-instrument-gate",
            "calibration":control,"overhead":overheads,"pass":passed,"completeCampaign":not early,
            "evidence":{k:{"run":v["label"],"frames":{s:len(d["intervalsUs"]) for s,d in v["scenes"].items()},
                           "summary":f"runs/{v['label']}/summary.json"} for k,v in runs.items()},
            "previousFailures":["gp-cal-4x","gp-cal-4x-retry"],
            "unstarted":[key for key in ORDER if key not in runs],
            "maxAccountingErrorMs":max(scene["gpu"]["maxErrorMs"] for run in runs.values()
                                       if run["enabled"] for scene in run["scenes"].values())}
    result["limits"]={"calibrationRatio":[3,5],"controlAbsoluteMs":0.10,"controlRelative":0.10,
                      "roiDisplayCodes":1,"meanOverheadPercent":3,"p95OverheadPercent":5,
                      "reconciliationMs":0.02}
    result["observedP7A"]={s:base["scenes"][s]["gpu"] for s in SCENES}
    for pair, scenes in overheads.items():
        for scene, values in scenes.items():
            for mode, key in (("off","gp-overhead-off-"),("on","gp-p7-")):
                d=runs[key+pair]["scenes"][scene]
                values[mode]={metric:d[metric] for metric in ("meanMs","p95Ms","p99Ms","fps")}
    if passed and not early:
        by_pack={}
        for version in ("p7","p8"):
            samples={s:[] for s in SCENES}
            for pair in ("a","b"):
                run=runs[f"gp-{version}-{pair}"]
                with (RUNS/run["label"]/"frames.csv").open() as stream:
                    frames=read_rows(stream)
                for s in SCENES:
                    d=run["scenes"][s]
                    samples[s].extend(collect_window(frames,range(d["firstId"],d["lastId"]+1)))
            by_pack[version]={s:gpu_stats(rows) for s,rows in samples.items()}
        result["pooled"]=by_pack
    save(R/"summary.json",result)
    print(json.dumps({k:v for k,v in result.items() if k not in ("pooled","observedP7A")},indent=2))
    return passed



def stopped_calibration():
    """Retain failed receipts without including loading frames in either room."""
    if any((RUNS/label).exists() for label in ORDER):
        raise ValueError("the resumed campaign already has receipts")
    runs={}
    for label in ("gp-cal-4x","gp-cal-4x-retry"):
        folder=RUNS/label
        receipt=read(folder/"complete.json")
        assert not receipt["complete"] and not receipt["screenshots"]
        pre=read(folder/"preflight.json")
        log=(folder/"client.log").read_text()
        hooks=re.findall(r"AQ_PROFILE_HOOK [^\n]+",log)
        with (BUILD/(label+".csv")).open() as stream:
            raw=read_rows(stream)
        validated_hooks=Counter(hooks)==Counter((BUILD/"injections.txt").read_text().splitlines())
        result={"label":label,"validated":False,"renderer":receipt["gl"],"seconds":receipt["seconds"],
                "observer":read(folder/"observer.json"),"hooks":hooks,"allFinalHookCountsMatch":validated_hooks,
                "loadingFramesWritten":len(raw),"acceptedFrames":0,"scenes":{s:None for s in SCENES},
                "firstProfilerException":re.search(r"^java\.(?:lang|util)\.\w+Exception: .+$",log,re.M)[0],
                "monitorForeignObservations":pre["foreignObservations"],"worldUnchanged":receipt["originalWorldAndConfigUnchanged"],
                "labUnchanged":pre["labBefore"]==pre["labAfter"]}
        save(folder/"summary.json",result)
        with (folder/"frames.csv").open("w") as stream:
            csv.writer(stream,lineterminator="\n").writerow(HEADER)
        runs[label]=result
    save(R/"summary.json",{"status":"stopped-after-calibration-retry","completeCampaign":False,"acceptedFrames":0,
         "thresholds":{"calibrationRatio":[3,5],"controlAbsMs":.1,"controlRelative":.1,"roiMaxCode":1,
                       "overheadMeanPercent":3,"overheadP95Percent":5,"maxAccountingErrorMs":.02},
         "calibration":None,"overhead":None,"reconciliation":None,"uncoveredPercent":None,"pooled":None,
         "completedAttempts":runs,"unstarted":list(ORDER)[1:]})


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    opt=parser.add_mutually_exclusive_group(required=True)
    opt.add_argument("--run")
    opt.add_argument("--stopped-calibration",action="store_true")
    opt.add_argument("--early",action="store_true")
    opt.add_argument("--gate-instrument",action="store_true")
    args=parser.parse_args()
    if args.stopped_calibration:
        stopped_calibration()
    elif args.run:
        result=summarize(args.run)
        print(result["label"],{s:len(d["intervalsUs"]) for s,d in result["scenes"].items()})
    else:
        sys.exit(0 if gates(args.early) else 1)
