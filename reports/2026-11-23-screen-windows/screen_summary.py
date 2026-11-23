"""Use only completed, render-guarded runs for the screen tile decision."""
import json
from screen_trials import HERE,ROOT,ROUTE,PACK,DIGEST,guarded
read=lambda p:json.loads(p.read_text())

def run():
    inputs={
      "noWindowBase":(ROUTE.parent/"2026-11-23-pane-beam/birch-control","birch-4"),
      "noWindowFull":(ROUTE/"selective-birch","birch-4"),"noWindowTiles":(HERE/"screen-birch","birch-4"),
      "rearBase":(ROUTE/"back-window-control-warm","birch-4"),"rearFull":(ROUTE/"back-window-selective-warm","birch-4"),
      "rearTiles":(HERE/"screen-rear","birch-4"),"redBase":(ROUTE.parent/"2026-11-23-pane-beam/control-reverse","red-ew"),
      "redFull":(ROUTE/"selective-room","red-ew"),"redTiles":(HERE/"screen-room","red-ew"),
      "airFull":(ROUTE/"selective-room","air"),"airTiles":(HERE/"screen-room","air")}
    timings={}
    for name,(folder,stage) in inputs.items():
        claim=read(folder/"summary.json"); receipt=read(folder/"complete.json"); pre=read(folder/"preflight.json")
        assert receipt["complete"] and receipt["shaderpackLogged"] and receipt["originalWorldAndConfigUnchanged"]
        assert not pre["foreignObservations"] and pre["labBefore"]==pre["labAfter"] and "3080 Ti" in claim["renderer"]["renderer"]
        if name.endswith("Tiles"):assert claim["packSha"]==DIGEST
        assert claim["packSha"]==receipt["packSha256"]
        scene=claim["scenes"][stage]
        timings[name]=dict(meanMs=scene["cpuMeanMs"],p99Ms=scene["cpuP99Ms"],frames=scene["frames"],folder=str(folder.relative_to(ROOT)))
    return {"pack":DIGEST,"timings":timings,"tiling":read(HERE/"screen-grid/edges.json"),
            "forestCoverage":read(HERE/"screen-birch-mask/edges.json"),"optics":read(HERE/"screen-optics/transmission.json"),
            "behind":read(HERE/"screen-behind-pane/comparison.json"),"normalLab":guarded.lab_check()["selected"]}
if __name__=="__main__":
    print(json.dumps(result:=run(),indent=2))
    (HERE/"result.json").write_text(json.dumps(result,indent=2)+"\n")
