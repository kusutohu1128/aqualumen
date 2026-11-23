"""Compare the staged shader with preview 8, preserving each scene and run order."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCENES = ("birch-0", "birch-1", "birch-4", "sand-4")
PAIRS = (("gp-density-p8-a","gp-density-tiles-a-retry1"), ("gp-density-p8-b","gp-density-tiles-b"))
EXPECTED = ("2989e6b5582935417bc5aa80f0e9e1c4f12a595b520f1c87f76c8f17a7fafe72",
            "a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9")

def compare(pairs):
    result={}
    for label,(baseline, candidate) in enumerate(pairs):
        a,b=[json.loads((HERE/run/"summary.json").read_text()) for run in (baseline,candidate)]
        assert (a["packSha"],b["packSha"]) == EXPECTED
        assert a["renderer"]["renderer"] == b["renderer"]["renderer"]
        geometry=[json.loads((HERE/run/"geometry.json").read_text()) for run in (baseline,candidate)]
        assert geometry[0]["sites"]==geometry[1]["sites"] and geometry[0]["time"]==geometry[1]["time"]
        for scene in SCENES:
            entry=result.setdefault(scene,[])
            old,new=a["scenes"][scene],b["scenes"][scene]
            rows={}
            for stage in ("frame","stage/shadowcomp","dispatch/shadowcomp3","dispatch/shadowcomp4","terrain/cutout","terrain/solid","terrain/translucent"):
                before,after=old["meanMs"][stage],new["meanMs"][stage]
                rows[stage]={"p8":before,"candidate":after,"delta":after-before}
            entry.append(dict(order="P8 then candidate" if label==0 else "candidate then P8",
                              baseline=baseline,candidate=candidate,stages=rows,
                              cpuFrameMeanMs=[old["cpuMeanMs"],new["cpuMeanMs"]],
                              cpuFrameP99Ms=[old["cpuP99Ms"],new["cpuP99Ms"]]))
    return result

if __name__=="__main__":
    results=compare(PAIRS)
    (HERE/"performance.json").write_text(json.dumps(results,indent=2)+"\n")
    for scene,pairs in results.items():
        print(scene,"frame",*[round(p["stages"]["frame"]["delta"],3) for p in pairs],
              "bounce",*[round(sum(p["stages"][s]["delta"] for s in ["dispatch/shadowcomp3","dispatch/shadowcomp4"]),3) for p in pairs])
