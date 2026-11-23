"""Compare the same surveyed birch position, four torches and timestamp instrumentation."""
from hashlib import sha256
import json
from packs import HERE, ROOT, BASE, package
def read(path): return json.loads(path.read_text())
def write():
    stock=ROOT/"dist/Aqualumen-1.9.0-preview.10.zip"
    tiled,_=package()
    density=HERE.parent/"2026-11-23-torch-density"
    cases={"base":(HERE.parent/"2026-11-23-oak-shadow/gp-density-oak-stock-b",stock),
           "leaf":(density/"gp-density-canopy-return-r2",BASE),"tiled":(density/"gp-density-leaf-tiles-a",tiled)}
    report={}; geometry=None
    for name,(directory,pack) in cases.items():
        summary=read(directory/"summary.json");complete=read(directory/"complete.json"); pre=read(directory/"preflight.json")
        assert complete["complete"] and sha256(pack.read_bytes()).hexdigest()==summary["packSha"]==complete["packSha256"]
        assert pre["labBefore"]==pre["labAfter"] and not pre["foreignObservations"]
        observed=read(directory/"geometry.json")
        if geometry is None: geometry=observed
        else: assert geometry==observed
        s=summary["scenes"]["birch-4"]
        report[name]=dict(path=str(directory.relative_to(ROOT)),packSHA=summary["packSha"],renderer=summary["renderer"]["renderer"],
            frames=s["frames"],frameIntervalMs=s["cpuMeanMs"],frameIntervalP99Ms=s["cpuP99Ms"],
            gpuFrameMs=s["meanMs"]["frame"],gpuExitMs=s["meanMs"]["dispatch/shadowcomp2"],
            gpuFirstReturnMs=s["meanMs"]["dispatch/shadowcomp3"],gpuSecondReturnMs=s["meanMs"]["dispatch/shadowcomp4"],
            gpuCutoutTerrainMs=s["meanMs"]["terrain/cutout"])
    (HERE/"timings.json").write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__":write()
