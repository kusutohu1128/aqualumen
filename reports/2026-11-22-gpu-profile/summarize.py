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

from profile_data import MEAN_OVERHEAD_PERCENT, P95_OVERHEAD_PERCENT, calibration, collect_window, overhead, percentile, read_rows
from zipfile import ZipFile
from comparisons import compare_packs, compared, root_means
import birch_scene
from run import BUILD, ORDER, PREVIEW_RUNS, OLDER_RUNS, PACKS, R, ROOT, RUNS, T, save, sha, latest, run_base

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
    geometry=read(folder/"geometry.json")
    birch=geometry.pop("birch",None)
    older=base in OLDER_RUNS
    scenes=birch_scene.STAGES if older else SCENES
    assert receipt["sourceDigest"]==historical["sourceDigest"] and geometry==read(T/"ceiling-isolated/geometry.json")
    assert receipt["stages"]==list(scenes) and bool(birch)==older
    if older:
        assert birch["pose"]==birch_scene.POSE and birch["time"]==9800
        assert read(folder/"birch-world.json")==birch_scene.audit_world()
        assert "[Server] AQ_BIRCH_RESTORED" in log
    assert receipt["gl"]["renderer"]==historical["gl"]["renderer"] and receipt["shaderpackLogged"] and receipt["complete"]
    assert not pre["foreignObservations"] and pre["labBefore"]==pre["labAfter"] and pre["samples"]>0
    assert observer["worldId"]=="b22dbccb-2970-41e6-847f-f183b1ec923d" and observer["frameObserverSha256"]==sha(BUILD/"frame-sample.jar")
    enabled="-off-" not in base
    hooks=re.findall(r"AQ_PROFILE_HOOK [^\n]+",log)
    stamps=[(s,extract(folder,s,None,pack_path=pack,condition=s if s in birch_scene.BIRCH else None)["intervalsUs"]) for s in scenes]
    result={"label":label,"pack":packname,"sha256":digest,"hooks":hooks,"enabled":enabled,"scenes":{}}
    result.update(startup=startup(label,log), profiledJar=observer.get("gpuProfilerSha256"),
                  cachePopulatedBefore=pre["cacheBefore"]["populated"],renderer=receipt["gl"],
                  cacheFilesBefore=pre["cacheFilesBefore"],worldUnchanged=receipt["originalWorldAndConfigUnchanged"],
                  labMetadata=pre["labAfter"]["metadata"])
    with ZipFile(pack) as z:
        sources=set(z.namelist())
        advertised={("dispatch/" if ext=="csh" else "quad/")+n
                    for path in sources for n,ext in re.findall(
                        r"^shaders/((?:begin|prepare|shadowcomp|deferred|composite|final)\d*)\.(csh|fsh)$",path)}
        props=dict(line.strip().split("=",1) for line in z.read("shaders/shaders.properties").decode().splitlines()
                   if line.strip() and not line.lstrip().startswith("#") and "=" in line)
        result["packEvidence"]={
            "programs":sorted(advertised),"absentPrograms":sorted(EXPECTED-advertised),
            "hasEntityProgram":"shaders/gbuffers_entities.fsh" in sources,
            "hasTexturedLit":"shaders/gbuffers_textured_lit.fsh" in sources,
            "hasShadowEntities":"shaders/shadow_entities.fsh" in sources,
            "separateEntityDrawsProperty":props.get("separateEntityDraws"),
            "areaSourceMarkerFiles":sorted(k for k in sources if k.endswith((".glsl",".fsh",".vsh",".csh"))
                                          and b"aqualumenAreaSourceLighting" in z.read(k)),
            "compilerApplicationLogs":re.findall(r"Compiling Aqualumen area lighting with NVIDIA function calls via ([^\n]+)",log)}
    if older:
        packfacts=result["packEvidence"]
        assert packfacts["hasShadowEntities"] and packfacts["hasTexturedLit"] and not packfacts["hasEntityProgram"]
        assert bool(packfacts["areaSourceMarkerFiles"])==bool(packfacts["compilerApplicationLogs"])==(arm=="p3")
        assert packfacts["separateEntityDrawsProperty"]==("true" if arm=="p3" else None)
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
            required=advertised
            if scene in birch_scene.BIRCH:
                data["birchImageCheck"]=birch_scene.image_check(folder,scene)
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
    runs={k:read(RUNS/latest(k)/"summary.json") for k in (PREVIEW_RUNS[:3] if early else PREVIEW_RUNS)}
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
                      "roiDisplayCodes":1,"meanOverheadPercent":MEAN_OVERHEAD_PERCENT,"p95OverheadPercent":P95_OVERHEAD_PERCENT,
                      "reconciliationMs":0.02}
    result["observedP7A"]={s:base["scenes"][s]["gpu"] for s in SCENES}
    for pair, scenes in overheads.items():
        for scene, values in scenes.items():
            for mode, key in (("off","gp-overhead-off-"),("on","gp-p7-")):
                d=runs[key+pair]["scenes"][scene]
                values[mode]={metric:d[metric] for metric in ("meanMs","p95Ms","p99Ms","fps")}
    if not early:
        result["pooled"],changes=compare_packs("p7","p8",SCENES,runs,RUNS,gpu_stats)
        result["comparisons"]={"p8MinusP7":changes}
    result["overheadPolicyChange"]={"previousMeanPercent":3,"previousP95Percent":5,
        "reason":"Range attribution in matched scenes; disclose CPU interval perturbation for each ABBA pair."}
    save(R/"summary.json",result)
    print(json.dumps({k:v for k,v in result.items() if k not in ("pooled","observedP7A","comparisons")},indent=2))
    return passed



def campaign():
    result=read(R/"summary.json")
    assert result["pass"] and set(result["overhead"])=={"a","b"}
    arms={k:read(RUNS/latest(k)/"summary.json") for k in ORDER}
    assert all(r["validated"] for r in arms.values())
    assert len({r["profiledJar"] for r in arms.values() if r["enabled"]})==1
    assert len({r["labMetadata"] for r in arms.values()})==1
    old,changes=compare_packs("stable","p3",birch_scene.STAGES,arms,RUNS,gpu_stats)
    result["pooled"].update(old)
    result["comparisons"]["p3MinusStable"]=changes
    torch={}
    for pack in ("stable","p3"):
        receipts=[arms[f"gp-{pack}-{i}"] for i in ("a","b")]
        runs=[r["scenes"] for r in receipts]
        names=set().union(*(row[s]["gpu"]["ranges"] for row in runs for s in birch_scene.BIRCH))
        torch[pack]={n:compared(*([row[s]["gpu"]["ranges"].get(n) for row in runs]
                                  for s in birch_scene.BIRCH)) for n in sorted(names)}
        off,on=birch_scene.BIRCH
        rows=[root_means(RUNS/r["label"]) for r in receipts]
        root_names=set().union(*(row[s] for row in rows for s in (off,on)))
        roots={}
        for key in sorted(root_names):
            a,b=[row[on].get(key,0)-row[off].get(key,0) for row in rows]
            roots[key]={"a":a,"b":b,"mean":(a+b)/2}
        assert abs(roots["frame"]["mean"]-sum(v["mean"] for k,v in roots.items() if k!="frame"))<1e-7
        cpu={k:mean(row[on][k]-row[off][k] for row in runs) for k in ("meanMs","fps","p95Ms")}
        result.setdefault("birchTorchMeanDifferences",{})[pack]={"meanFrameContributionsMs":roots,"cpu":cpu}
    result["birchTorchMinusOff"]=torch
    result["status"]="completed"
    result["unstarted"]=[]
    result["rejectedRoomBirchAttempts"]={}
    for base in OLDER_RUNS:
        if arms[base]["label"]!=base:
            rejected=read(RUNS/base/"summary.json")
            assert rejected["validated"] is False
            result["rejectedRoomBirchAttempts"][base]={"reason":rejected["reason"],
                    "receipt":f"runs/{base}/summary.json","replacement":arms[base]["label"]}
    for k,r in arms.items():
        result["evidence"][k]={"run":r["label"],"frames":{s:len(d["intervalsUs"]) for s,d in r["scenes"].items()},
                              "summary":f"runs/{r['label']}/summary.json"}
    result["maxAccountingErrorMs"]=max(d["gpu"]["maxErrorMs"] for r in arms.values() if r["enabled"]
                                       for d in r["scenes"].values())
    result["packEvidence"]={p:arms[f"gp-{p}-b"]["packEvidence"] for p in result["pooled"]}
    result["interpretation"]={
        "units":"GPU elapsed timestamps in ms; CPU render-return intervals include swap. Two measured orders.",
        "pooled":"Nearest-rank percentiles across accepted frames from both orders for each pack and scene.",
        "paired":"Newer minus older within A and B; mean weights the two orders equally. Percentile deltas are non-additive.",
        "decomposition":"Mean deltas of direct frame children plus uncovered time add to the mean GPU frame delta.",
        "roomContrast":"Night versus noon also changes the roof and time; use the matched birch torch toggle for lamp cost.",
        "roomProjection":"Same physical room, pose and base FOV. The 1.8.0/p3 pair uses FOV effects 1.0, the p7/p8 pair 0.0. The older view is wider (central crop factor 1.136 matches landmarks). p7 is context only across pairs.",
        "rangeLimits":"Elapsed ranges include waits and batched submissions. No shader instruction, register, occupancy, lamp-ray or water-only counter.",
        "entities":"Iris 1.8.8 Entities falls back to TexturedLit for stable and p3. separateEntityDraws defaults false on stable and is true on p3.",
        "overheadApplicability":"Direct overhead controls were acquired on p7 rooms. Older packs and birch have profiled measurements only."}
    save(R/"summary.json",result)


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
    opt.add_argument("--campaign", action="store_true")
    opt.add_argument("--stopped-calibration",action="store_true")
    opt.add_argument("--early",action="store_true")
    opt.add_argument("--gate-instrument",action="store_true")
    args=parser.parse_args()
    if args.campaign:
        campaign()
    elif args.stopped_calibration:
        stopped_calibration()
    elif args.run:
        result=summarize(args.run)
        print(result["label"],{s:len(d["intervalsUs"]) for s,d in result["scenes"].items()})
    else:
        sys.exit(0 if gates(args.early) else 1)
