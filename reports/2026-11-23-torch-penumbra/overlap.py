"""Measure a moving hand torch, an oak column and a cow in the same private scene."""
import sys
from copy import copy
from hashlib import sha256
from zipfile import ZipFile
from pack import HERE, WORK, edit
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-umbra"))
from moving import A, CACHE, COMPILER, guarded

# column, cow x, camera x. The animal faces north, on the player's side
# of the column. These are diagnostic coordinates in the guarded test room.
POSES={"open":(False,None,A),"column":(True,None,A),"cow-west":(False,405.60,A),
       "mixed-west":(True,405.60,A),"cow-centre":(False,406.45,A),"mixed-centre":(True,406.45,A),
       "mixed-shift":(True,406.45,A+.24),"cow-shift":(False,406.45,A+.24),
       "column-shift":(True,None,A+.24),"column-again":(True,None,A),"open-again":(False,None,A)}
CENTRE={name:POSES[name] for name in ("open","column","cow-centre","mixed-centre","mixed-shift","cow-shift","column-shift","open-again")}
FOLIAGE={"leaf":(False,None,A),"column-leaf":(True,None,A),"leaf-cleared":(True,None,A)}
LEAF_CELL="405 152 -410"
STUDY_SHA="4a0c68c66a5ded34e2d46ebe38d24c32177fbee2385271f0f01dd594aa34f096"


JOINT_SHA="3fd9a38e39b8a4be6a48355bf76876e03535866923f6f14277b0f0607e0ecbf8"


def meter(joint=False,vertex=False):
    pack=WORK/("Aqualumen-Hand-Penumbra.zip" if joint else "Aqualumen-Torch-Penumbra.zip")
    assert sha256(pack.read_bytes()).hexdigest()==(JOINT_SHA if joint else STUDY_SHA)
    out=WORK/("Aqualumen-Joint-Shadow-Meter.zip" if joint else "Aqualumen-Overlapping-Shadow-Meter.zip")
    # Hold the ordinary render and texture producer fixed while the meter
    # queries each visibility function against that very same GPU frame.
    if vertex:
        out=WORK/("Aqualumen-Joint-Vertex-Meter.zip" if joint else "Aqualumen-Area-Vertex-Meter.zip")
    with ZipFile(pack) as src, ZipFile(WORK/"Aqualumen-Torch-Penumbra.zip") as beauty, ZipFile(out,"w") as dst:
        for info in beauty.infolist():
            data=beauty.read(info)
            if info.filename=="shaders/lib/local_lighting.glsl":
                debug=edit(src.read(info.filename),b"vec3 lampVisibility(",b"bool includeArea=true;\nvec3 lampVisibility(")
                gate=b"carried" if joint else b"!testBody"
                term=gate+b" && !occluders.leafVolume"
                debug=edit(debug,b"if("+term+b")",b"if(includeArea && "+term+b")")
                diagnostic=copy(info)
                diagnostic.filename="shaders/lib/overlap_lighting.glsl"
                dst.writestr(diagnostic,debug)
            if vertex and info.filename=="shaders/final.vsh":
                data=(HERE/"meter_source.vsh").read_bytes()
            if info.filename=="shaders/final.fsh":
                data=edit(data,b"void main() {",b'#include "/lib/overlap_lighting.glsl"\n'+(HERE/"overlap_meter.glsl").read_bytes()+b"""
void main() {
    ivec2 meterPixel=ivec2(gl_FragCoord.x,viewHeight-gl_FragCoord.y)-ivec2(16);
    if(all(greaterThanEqual(meterPixel,ivec2(0))) && all(lessThan(meterPixel,ivec2(128,48)))) {
        gl_FragColor=vec4(overlapReadout(meterPixel),1.);
        return;
    }""")
                if vertex:
                    start=data.index(b"    int row=lampLinear(ivec3(p)/8,8);")
                    stop=data.index(b"    vec3 l=normalize(source-p);",start)
                    data=data[:start]+b"""    if(meterList.y!=1) return vec3(vec2(meterList)/255.,17./255.);
    vec3 source=meterLamp.xyz;
"""+data[stop:]
                    data=edit(data,b"vec3 overlapReadout(",b"flat in vec4 meterLamp;\nflat in ivec2 meterList;\nvec3 overlapReadout(")
            dst.writestr(info,data)
    return out


class Overlap:
    def __init__(self,base,poses=POSES,cow_z=-408.75):
        self.base=base
        self.poses=poses
        self.cow_z=cow_z
        for name,(_,x,_) in self.poses.items():
            base.STAGE_TABLE[name]=(False,False,None if x is None else (x,151,self.cow_z),"white_concrete",True,18000)
    def __getattr__(self,key):
        return getattr(self.base,key)
    def self_test(self,names):
        assert names==list(self.poses)
    def geometry(self,names):
        return {"wallZ":-412,"column":[406,151,-410],"cowZ":self.cow_z,"poses":self.poses,"yawPitch":[180,4],
                "diskRays":[96,96],"worldSampleOrigin":[404.96,151.14,-412],"leafCell":LEAF_CELL if "leaf" in self.poses else None}
    def datapack(self,names):
        files=self.base.datapack(names)
        prefix="data/animal/function/"
        for i,(name,(log,x,camera)) in enumerate(self.poses.items()):
            key=prefix+f"s{i}.mcfunction"
            body=files[key]
            block="oak_log" if log else "air"
            items=f"item replace entity {self.PLAYER} weapon.mainhand with torch"
            body=edit(body,f"tp {self.PLAYER} {self.POSE}",f"tp {self.PLAYER} {camera} 151 -407.25 180 4\n{items}\nfill 406 151 -410 406 152 -410 {block}")
            if x is not None:
                body=edit(body,f"tp {self.SELECT} {x} 151 {self.cow_z} 90 0",f"tp {self.SELECT} {x} 151 {self.cow_z} 180 0")
            if "leaf" in self.poses:
                material="birch_leaves[persistent=true]" if name in ("leaf","column-leaf") else "air"
                body=edit(body,f"say AQLAVA_BEGIN_{name}_END",f"setblock {LEAF_CELL} {material}\nsay AQLAVA_BEGIN_{name}_END")
            files[key]=body
            for stage in ("v","e"):
                ck=prefix+f"{stage}{i}.mcfunction"
                check=edit(files[ck],"if block 406 152 -410 air",f"if block 406 151 -410 {block} if block 406 152 -410 {block} if items entity {self.PLAYER} weapon.mainhand minecraft:torch")
                check=edit(check,"positioned 409.48 151 -405.95",f"positioned {camera} 151 -407.25")
                check=edit(check,"x_rotation=6.95..7.05,y_rotation=153.75..153.85","x_rotation=3.95..4.05,y_rotation=179.95..-179.95")
                if "leaf" in self.poses:
                    check=edit(check,f"if block 406 152 -410 {block}",f"if block 406 152 -410 {block} if block {LEAF_CELL} {material}")
                files[ck]=check
        return files


if __name__=="__main__":
    pack=meter("joint" in sys.argv[1],"vertex" in sys.argv[1])
    if sys.argv[1].startswith("build"):
        print(sha256(pack.read_bytes()).hexdigest())
    else:
        label,=sys.argv[1:]
        poses,cow_z=(CENTRE,-408.40) if label.endswith("-centre") else (POSES,-408.75)
        if "joint" in label:
            poses={**poses,**FOLIAGE}
        fixed={"backend":"vgl","size":"1280x720","settle":"1","shot-gap":".15","period-ticks":"180",
               "glcache":str(CACHE),"compiler-mod":str(COMPILER),"stages":",".join(poses)}
        guarded.launch(pack,label,"off",fixed,HERE,lambda base:Overlap(base,poses,cow_z))
