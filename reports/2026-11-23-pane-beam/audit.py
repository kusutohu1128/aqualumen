"""Verify evidence provenance and assemble both orderings of the ordinary frame timings."""
import json
from zipfile import ZipFile
from window_room import HERE, ROOT, PREV, PACKS, guarded
from score import reader
from beam_pack import meter

def read(p): return json.loads(p.read_text())
def audit():
    report={}
    lab=guarded.lab_check()
    assert lab==read(PREV/"verification.json")["currentLab"]
    runs={}
    timings={}
    groups={"control":(PREV/"timing-sun-at-night",HERE/"control-reverse"),
            "candidate":(HERE/"candidate-night",HERE/"candidate-reverse"),
            "cells":(HERE/"cells-night",HERE/"cells-reverse")}
    for role,folders in groups.items():
        pack=ROOT/"dist"/("Aqualumen-"+PACKS[role][0]+".zip")
        assert guarded.sha(pack)==PACKS[role][1]
        timings[role]={}
        for k,folder in zip(("airThenGlass","glassThenAir"),folders):
            s=read(folder/"summary.json")
            assert s["packSha"]==PACKS[role][1] and "3080 Ti" in s["renderer"]["renderer"]
            first,last=("air","red-ew") if k=="airThenGlass" else ("red-ew","air")
            assert s["scenes"][first]["lastFrame"]<s["scenes"][last]["firstFrame"]
            for stage in (first,last):
                assert reader.check_record(folder,folder/(stage+"-ingame.png"))==PACKS[role][1]
            timings[role][k]={s:{k:v for k,v in row.items() if k in ("cpuMeanMs","cpuP99Ms","frames")} for s,row in s["scenes"].items()}
    for role,folder in (("candidate","candidate-rgb"),("cells","cells-rgb"),("control","control-extra")):
        name,digest=PACKS[role];pack=ROOT/"dist"/f"Aqualumen-{name}.zip"
        expect=guarded.sha(meter(pack,role))
        folder=HERE/folder; receipt=read(folder/"complete.json")
        for s in receipt["stages"]:
            assert reader.check_record(folder,folder/(s+"-ingame.png"))==expect
        runs[folder.name]=expect
    builds={}
    baseline=ROOT/"dist/Aqualumen-Sunlit-Panes.zip"
    for role in ("candidate","cells"):
        with ZipFile(baseline) as old,ZipFile(ROOT/"dist"/("Aqualumen-"+PACKS[role][0]+".zip")) as pack:
            assert not(set(old.namelist())-set(pack.namelist()))
            diffs=[k for k in pack.namelist() if k not in old.NameToInfo or old.read(k)!=pack.read(k)]
        expected={"candidate":["lib/pane_beam.glsl","lib/local_lighting.glsl","lib/leaf_disk.glsl"],
                  "cells":["lib/window_cells.glsl","lib/window_disk.glsl","lib/local_lighting.glsl","shadowcomp5.csh","shadowcomp6.csh","shaders.properties"]}
        assert set(diffs)=={"shaders/"+s for s in expected[role]}
        output=HERE if role=="candidate" else HERE/"cells-compile"
        for vendor in ("mesa","nvidia"):
            log=(output/f"compile-{vendor}.txt").read_text()
            assert sum(s.startswith("PASS ") for s in log.splitlines())==38
        builds[role]=dict(sha256=PACKS[role][1],changedMembers=diffs)
    for name in ("control-extra","candidate-rgb","cells-rgb","grove-edits","candidate-night","control-reverse","candidate-reverse","cells-night","cells-reverse"):
        r=read(HERE/name/"preflight.json")
        assert r["labBefore"]==r["labAfter"]==lab and not r["foreignObservations"]
    for name in ("comparison.json","cells-comparison.json"):
        stages=read(HERE/name)["stages"]
        report[name]=dict(pairs=sum(r["paired"] for r in stages.values()),different=sum(r["differing"] for r in stages.values()),
                          beyondOne=sum(r["moreThanOneByte"] for r in stages.values()),maxBytes=max(r["maximumBytes"] for r in stages.values()))
    other={}
    for role in ("control","cells"):
        for label in ("birch-"+role,"gp-window-"+role+"-profile","gp-window-birch-"+role+"-profile"):
            f=HERE/label; summary=read(f/"summary.json")
            assert summary["packSha"]==PACKS[role][1]
            for stage in summary["scenes"]: reader.check_record(f,f/(stage+"-ingame.png"))
            profiled=label.endswith("profile")
            other[label]={
                stage: row["meanMs"] if profiled else {k:row[k] for k in ("cpuMeanMs","cpuP99Ms","frames")}
                for stage,row in summary["scenes"].items()}
    report.update(timings=timings,additionalMeasurements=other,builds=builds,readouts=runs,lab=lab)
    (HERE/"audit.json").write_text(json.dumps(report,indent=2)+"\n")

if __name__=="__main__": audit()
