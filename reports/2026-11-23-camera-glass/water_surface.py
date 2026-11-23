"""Measure the water surface's own outgoing light with a pane on either side."""
from room import HERE,ROOT,STUDY,Room,LAYOUT,guarded,ArchiveEntry,zip_bytes,meter
from zipfile import ZipFile
from pathlib import Path
import sys
STAGES=("pool","front-pane","rear-pane","pool-cleared")
POSE="406.375 153 -406.5 180 47"
class Pool(Room):
    def __init__(self,base):
        for stage in STAGES:LAYOUT[stage]={}
        super().__init__(base)
    def geometry(self,names):
        return dict(self.base.geometry(names),camera=POSE,poolInterior=[[405,151,-410],[407,151,-409]],
                    paneLayers={"front-pane":[-408,153,154],"rear-pane":[-411,151,152]})
    def datapack(self,names):
        base=self.base;files=base.datapack(names)
        for i,name in enumerate(names):
            front=name=="front-pane";rear=name=="rear-pane"
            a="red_stained_glass_pane" if front else "air"
            b="red_stained_glass_pane" if rear else "air"
            stage=["gamemode spectator "+base.PLAYER,
                   "fill 404 151 -411 408 151 -408 glass","fill 405 151 -410 407 151 -409 water[level=0]",
                   "fill 405 151 -411 407 152 -411 air","fill 405 151 -411 407 151 -411 glass",
                   f"fill 405 153 -408 407 154 -408 {a}",f"fill 405 152 -411 407 152 -411 {b}",
                   "setblock 406 150 -409 sea_lantern"]
            checks=["if block 406 150 -409 sea_lantern","if block 406 151 -409 water[level=0]",
                    "if block 406 151 -410 water[level=0]","if block 406 151 -411 glass",
                    f"if block 406 152 -411 {b}",f"if block 406 153 -408 {a}",f"if block 406 154 -408 {a}"]
            marker=f"say AQLAVA_BEGIN_{name}_END"
            k=f"data/animal/function/s{i}.mcfunction"
            files[k]=files[k].replace(f"tp {base.PLAYER} {base.POSE}",f"tp {base.PLAYER} {POSE}").replace(marker,"\n".join(stage+[marker]))
            for phase in "ve":
                k=f"data/animal/function/{phase}{i}.mcfunction"
                files[k]=files[k].replace("positioned 409.48 151 -405.95","positioned "+POSE.rsplit(" ",2)[0]).replace(
                    "x_rotation=6.95..7.05,y_rotation=153.75..153.85","x_rotation=46.95..47.05,y_rotation=179.95..180.05").replace(
                    "if block 406 152 -410 air"," ".join(checks))
        return files
def water_meter():
    # Only water emits the alternating test signal. All actual overlying
    # materials, source coordinates and the candidate's view path stay active.
    base=meter(STUDY)
    with ZipFile(base) as z:files={k:z.read(k) for k in z.namelist()}
    k="shaders/lib/window_scene.glsl"
    s=files[k].decode()
    line="color=vec3((int(gl_FragCoord.x)&1)==0?.75:.25);"
    assert s.count(line)==1
    files[k]=s.replace(line,"color=vec3(.25);").encode()
    k="shaders/gbuffers_water.fsh"
    s=files[k].decode()
    line="gl_FragData[0]=vec4(max(color,vec3(0.0))*paneToEye(worldPosition),1.0);"
    assert s.count(line)==1
    files[k]=s.replace(line,"color=vec3((int(gl_FragCoord.x)&1)==0?.75:.25);\n    "+line).encode()
    data=zip_bytes(tuple(ArchiveEntry(k,v) for k,v in sorted(files.items())))
    out=ROOT/"build/camera-glass/Aqualumen-Glass-Water-Surface-Meter.zip"
    if out.exists() and out.read_bytes()!=data: raise ValueError("Meter output changed")
    out.write_bytes(data)
    return out
if __name__=="__main__":
    label=sys.argv[1];assert not (HERE/label).exists()
    pack=water_meter() if "--meter" in sys.argv else STUDY
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(STAGES),glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"210","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(pack,label,"off",fixed,HERE,Pool)
