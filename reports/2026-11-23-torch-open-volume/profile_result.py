"""Summarize native timer ranges on matching, verified stage windows."""
import json
from results import DENSITY,HERE,PACKS,read,receipt

RANGES={
    "frame":"frame","solidTerrain":"terrain/solid","foliage":"terrain/cutout","visibleTerrain":"quad/deferred",
    "firstBounce":"dispatch/shadowcomp2","secondBounce":"dispatch/shadowcomp4",
    "changeDetection":"dispatch/shadowcomp5","rebuildClearPaths":"dispatch/shadowcomp6",
    "atmospherePrepare":"pass/prepare4",
}


def atlas():
    output={}
    for arm,mode,ns in (("control","control",[0,4]),("cell","cell",[0,1,2,4])):
        path=DENSITY/("gp-density-open-volume-gpu-"+arm)
        run=receipt(path,PACKS[mode][1])
        assert run["stages"]==[f"birch-{n}" for n in ns] and run["size"]==[2560,1440]
        assert read(path/"observer.json")["gpuProfilerSha256"]=="75d6e7307d9437c3aa165d25530878ea7f42456644e7112713728cc2c918ea20"
        assert read(path/"geometry.json")["sites"]==read(DENSITY/"gp-density-open-volume-control-a/geometry.json")["sites"]
        result={}
        for n in ns:
            s=read(path/"summary.json")["scenes"][f"birch-{n}"]
            values=s["meanMs"]
            means={label:values[key] for label,key in RANGES.items() if key in values}
            assert ("changeDetection" in means)==(arm=="cell") and ("rebuildClearPaths" in means)==(arm=="cell")
            # Preserve every named range. Nested parent and child intervals overlap.
            result[str(n)]=dict(frames=s["frames"],cpuObservedMs=s["cpuMeanMs"],
                meanGpuMs=means,allMeanGpuMs=values,first=s["firstFrame"],last=s["lastFrame"])
        output[arm]=result
    return output


if __name__=="__main__":
    tables=atlas()
    (HERE/"gpu-times.json").write_text(json.dumps(tables,indent=2,allow_nan=False)+"\n")
    for arm,rows in tables.items():
        for n,row in rows.items():
            print(arm,n,{k:round(v,3) for k,v in row["meanGpuMs"].items()})
