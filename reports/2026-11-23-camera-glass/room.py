"""Capture an ordinary view or differential background radiance in the guarded room."""
import argparse
import hashlib
import sys
from pathlib import Path
from zipfile import ZipFile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE.parent/"2026-11-23-stained-panes"),str(ROOT/"tools")]
from glass_room import Room, LAYOUT, state, guarded
from land_shadow_pack import ArchiveEntry,zip_bytes

BASE=ROOT/"dist/Aqualumen-Window-Tiles.zip"
STUDY=ROOT/"dist/Aqualumen-Camera-Glass.zip"
POSE="406.38 151 -406.5 180 0"
ANGLE="408.2 151 -406.5 150 0"
INSIDE="406.38 151 -409.5 180 0"
def sheet(z,dye):
    return {(x,z):dye+"_stained_glass_pane" for x in (405,406,407)}
red=sheet(-410,"red")
LAYOUT.update({"none":{}, "one":red,"blue":sheet(-410,"blue"),"twice":red|sheet(-412,"red"),
               "mix":red|sheet(-412,"blue"),"reverse":sheet(-410,"blue")|sheet(-412,"red"),
               "oblique":red,"inside":red,"front":red,"removed":{}})
STAGES=("none","one","blue","twice","mix","reverse","oblique","inside","front","removed")
def pose(stage):
    return ANGLE if stage=="oblique" else INSIDE if stage=="inside" else POSE
class GlassRoom(Room):
    def geometry(self,names):
        return dict(super().geometry(names),camera={s:pose(s) for s in names},
                    receiver="sea lantern at (406,152,-413), foreground at (406,152,-408) in front stage")
    def datapack(self,names):
        # Use the original room builder and exact world UUID, with new block and pose witnesses.
        base=self.base
        files=base.datapack(names)
        for i,stage in enumerate(names):
            layout=LAYOUT[stage]
            marker=f"say AQLAVA_BEGIN_{stage}_END"
            fg="sea_lantern" if stage=="front" else "air"
            place=["gamemode spectator "+base.PLAYER,"fill 405 151 -412 407 152 -408 air",
                   "setblock 406 152 -413 sea_lantern",f"setblock 406 152 -408 {fg}"]
            for x,z in layout:
                place.append(f"fill {x} 151 {z} {x} 152 {z} {state(layout,x,z)}")
            # The wall adjacent to the northern sheet is solid. Let Minecraft
            # resolve connections and verify the actual state on both receipts.
            def actual(x,z):
                if z==-412:
                    return state(layout,x,z).replace("north=false","north=true")
                return state(layout,x,z)
            checks=[]
            for z in (-412,-411,-410,-409):
                for x in (405,406,407):
                    for y in (151,152):
                        mat=actual(x,z) if (x,z) in layout else "air"
                        checks.append(f"if block {x} {y} {z} {mat}")
            # Specify the physical connections, including the chamber wall.
            place=[s.replace("north=false","north=true") if " -412 " in s and "stained_glass_pane" in s else s for s in place]
            k=f"data/animal/function/s{i}.mcfunction"
            assert files[k].count(marker)==1
            files[k]=files[k].replace(f"tp {base.PLAYER} {base.POSE}",f"tp {base.PLAYER} {pose(stage)}").replace(marker,"\n".join(place+[marker]))
            for typ in "ve":
                k=f"data/animal/function/{typ}{i}.mcfunction"
                old="positioned "+base.POSE.rsplit(" ",2)[0]
                yaw=pose(stage).split()[-2]
                files[k]=files[k].replace(old,"positioned "+pose(stage).rsplit(" ",2)[0]).replace(
                    "x_rotation=6.95..7.05,y_rotation=153.75..153.85",f"x_rotation=-0.05..0.05,y_rotation={float(yaw)-.05}..{float(yaw)+.05}").replace(
                    "if block 406 152 -413 white_concrete","if block 406 152 -413 sea_lantern").replace(
                    "if block 406 152 -410 air"," ".join(checks)+f" if block 406 152 -408 {fg}")
        return files

def meter(pack):
    with ZipFile(pack) as z: entries={k:z.read(k) for k in z.namelist()}
    k="shaders/lib/window_scene.glsl"
    src=entries[k].decode()
    anchor="    gl_FragData[0]=vec4(color"
    assert src.count(anchor)==1
    entries[k]=src.replace(anchor,"    color=vec3((int(gl_FragCoord.x)&1)==0?.75:.25);\n"+anchor).encode()
    read="#version 330 compatibility\nuniform sampler2D colortex0;\n/* DRAWBUFFERS:0 */\nvoid main(){gl_FragData[0]=texelFetch(colortex0,ivec2(gl_FragCoord.xy),0);}\n"
    entries["shaders/composite.fsh"]=read.encode()
    entries["shaders/final.fsh"]=read.encode()
    data=zip_bytes(tuple(ArchiveEntry(k,v) for k,v in sorted(entries.items())))
    out=ROOT/"build/camera-glass"/(pack.stem+"-Meter.zip")
    if out.exists() and out.read_bytes()!=data: raise ValueError("Meter output changed")
    out.write_bytes(data)
    return out
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("label");p.add_argument("pack",choices=["base","study"]);p.add_argument("--meter",action="store_true")
    p.add_argument("stages",nargs="*")
    args=p.parse_intermixed_args()
    source={"base":BASE,"study":STUDY}[args.pack]
    assert guarded.sha(BASE)=="4a3f9b865ba9ddc727e8a0ff3e703c3843f6ca84c212d109d42d0e558fe0d802"
    assert not (HERE/args.label).exists()
    pack=meter(source) if args.meter else source
    selected=args.stages or STAGES
    assert set(selected)<=set(STAGES)
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(selected),glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"200","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(pack,args.label,"off",fixed,HERE,GlassRoom)
