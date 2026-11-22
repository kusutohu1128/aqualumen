"""Compare pack medians within each ABBA pair and reconcile mean frame-time differences."""
from collections import defaultdict
from statistics import mean
import csv

from profile_data import collect_window, read_rows


def compared(left, right):
    """Use newer minus older in both orders, even when the newer pack ran first."""
    def paired(metric):
        if any(value is None for value in (*left,*right)):
            return None
        a,b=[r[metric]-l[metric] for l,r in zip(left,right,strict=True)]
        return {"a":a,"b":b,"mean":(a+b)/2}
    return {"medianMs":paired("medianMs"),"p95Ms":paired("p95Ms")}


def root_means(folder):
    times=defaultdict(lambda:defaultdict(int))
    frames=defaultdict(set)
    with (folder/"frames.csv").open() as stream:
        for row in csv.DictReader(stream):
            scene=row["scene"]
            if row["range"]=="frame":
                frames[scene].add(int(row["frame"]))
            if int(row["parent"]) in (-1,0):
                times[scene][row["range"]]+=int(row["end_ns"])-int(row["start_ns"])
    result={}
    for scene,totals in times.items():
        whole=totals.pop("frame")
        totals["uncovered"]=whole-sum(totals.values())
        assert min(totals.values())>=0
        result[scene]={k:v/(1e6*len(frames[scene])) for k,v in totals.items()}
        result[scene]["frame"]=whole/(1e6*len(frames[scene]))
    return result


def compare_packs(old,new,scenes,arms,runs_dir,gpu_stats):
    packs=(old,new)
    runs={p:[arms[f"gp-{p}-{k}"] for k in ("a","b")] for p in packs}
    totals={p:[root_means(runs_dir/r["label"]) for r in runs[p]] for p in packs}
    pooled={}
    for pack,receipts in runs.items():
        samples={s:[] for s in scenes}
        for r in receipts:
            with (runs_dir/r["label"]/"frames.csv").open() as stream:
                frames=read_rows(stream)
            for s in scenes:
                d=r["scenes"][s]
                samples[s].extend(collect_window(frames,range(d["firstId"],d["lastId"]+1)))
        pooled[pack]={s:gpu_stats(rows) for s,rows in samples.items()}
    result={}
    for s in scenes:
        metrics={p:[r["scenes"][s]["gpu"] for r in runs[p]] for p in packs}
        names=set().union(*(set(d["ranges"]) for p in packs for d in metrics[p]))
        def distribution(d,name):
            return d["residual"] if name=="uncovered" else d["ranges"].get(name)
        delta={name:compared(*([distribution(d,name) for d in metrics[p]] for p in packs))
               for name in sorted(names|{"uncovered"})}
        # Only frame's direct children enter this additive decomposition. A stage can be empty.
        names=set().union(*(row[s] for p in packs for row in totals[p]))
        contributions={}
        for name in sorted(names):
            pair=[totals[new][i][s].get(name,0)-totals[old][i][s].get(name,0) for i in (0,1)]
            contributions[name]={"a":pair[0],"b":pair[1],"mean":mean(pair)}
        for column in ("a","b","mean"):
            assert abs(sum(v[column] for k,v in contributions.items() if k!="frame")-contributions["frame"][column])<1e-7
        cpu={m:mean(b["scenes"][s][m]-a["scenes"][s][m] for a,b in zip(runs[old],runs[new]))
             for m in ("meanMs","p95Ms","fps")}
        result[s]={"paired":delta,"meanFrameContributionsMs":contributions,"pairedMeanCpuDifference":cpu}
    return pooled,result
