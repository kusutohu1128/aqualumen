"""Read all completed scenes and verify that the selected Lab and public ZIP agree."""
from hashlib import sha256
import json
import sys
from zipfile import ZipFile
from pack import HERE,ROOT,WORK
from score import DENSITY,check_record

def read(path):return json.loads(path.read_text())
def digest(path):return sha256(path.read_bytes()).hexdigest()
release=ROOT/"dist/Aqualumen-Placed-Penumbra-Study.zip"
public=digest(release)
assert public=="b224ea6f9424ad7dd8424f2c192e1708f97f734a802870cea42ebb722dcb4c02"
with ZipFile(release) as a,ZipFile(WORK/"Aqualumen-Placed-Penumbra-Hull.zip") as b:
    assert sorted(a.namelist())==sorted(b.namelist())
    assert all(a.read(n)==b.read(n) for n in a.namelist())
    members=len(a.namelist())
scenes={}
for folder in (HERE/"grove-hull-meter",HERE/"grove-release",HERE/"cow-and-trunk",
               *(DENSITY/("gp-density-placed-hull-"+name) for name in ("meter","coordinates","ordinary","control","gpu"))):
    r=read(folder/"complete.json")
    for stage in r["stages"]:check_record(folder,folder/(stage+"-ingame.png"))
    scenes[folder.name]=dict(sha=r["packSha256"],renderer=r["gl"]["renderer"],size=r["size"],stages=r["stages"])
assert scenes["grove-release"]["sha"]==scenes["gp-density-placed-hull-ordinary"]["sha"]==scenes["gp-density-placed-hull-gpu"]["sha"]==public
sys.path.insert(0,str(HERE.parent/"2026-11-22-gpu-profile"))
import run as guarded
lab=guarded.lab_check()
for name in scenes:
    folder=HERE/name if (HERE/name).exists() else DENSITY/name
    pre=read(folder/"preflight.json")
    assert pre["labBefore"]==pre["labAfter"]==lab
assert lab["selected"]=="Aqualumen-1.8.0.zip"
native=[(HERE/("hull-cache-"+driver+".log")).read_text().splitlines() for driver in ("10_nvidia","50_mesa")]
assert native[0][1:]==native[1][1:] and "RTX 3080 Ti" in native[0][0] and "llvmpipe" in native[1][0]
rows=[line.split() for line in native[0][1:]]
timing={}
for tag in ("ordinary","control","gpu"):
    folder=DENSITY/("gp-density-placed-hull-"+tag)
    scene=read(folder/"summary.json")["scenes"]["birch-4"]
    timing[tag]={k:scene[k] for k in ("frames","cpuMeanMs","cpuP99Ms")}
    if tag=="gpu": timing[tag]["meanGpuMs"]=scene["meanMs"]
evidence=dict(sha=public,identicalShaderFilesAndLicense=members,scenes=scenes,lab=lab,timing=timing,
              native=dict(transitions=len(rows),receiverEmitterChecks=sum(int(r[1]) for r in rows),
                          cuboidsChecked=sum(int(r[4]) for r in rows)))
(HERE/"verification.json").write_text(json.dumps(evidence,indent=2)+"\n")
