"""Move one opaque cube around one floor torch on a private night-time grass platform."""
import sys
from pack import HERE,ROOT,WORK,build,replace
from orthogonal import instrument
sys.path.insert(0,str(HERE.parent/"2026-11-22-gpu-profile"))
import run as guarded

NAME="Aqualumen-Placed-Torch-Neighbours.zip"
CUBES={"north-east":(406,151,-409),"north":(405,151,-409),"east":(406,151,-408),
       "south-east":(406,151,-407),"two-east":(407,151,-408)}
POSE="406.5 156 -409.5 0 89"
TORCH="405 151 -408"

def screen(name,s):
    s=instrument(name,s)
    if name=="shaders/final.fsh":
        a=s.index("    ivec2 pixelHere=");b=s.index("    gl_FragColor=vec4(rgb,1.);",a)
        s=s[:a]+"""    ivec2 px=ivec2(gl_FragCoord.xy);
    int group=px.x/12,side=(px.x%12)/6,lane=px.x%6;
    ivec2 q=ivec2(12*group+side,px.y);
    vec4 lamps=texelFetch(colortex1,q,0),position=texelFetch(colortex2,q,0);
    vec3 offset=texelFetch(colortex3,q,0).rgb;
    ivec3 bits=ivec3(round(clamp(offset+vec3(.03),vec3(0),vec3(.06))*1048576.));
    vec3 rgb;
    if(lane==0) rgb=probeBytes(int(lamps.x));
    else if(lane<4) rgb=probeBytes(int(round(clamp(position[lane-1],0.,127.)*65536.)));
    else rgb=(lane==4?vec3(bits&ivec3(255)):vec3(bits>>8))/255.;
    if(px.y==2 && px.x<256) rgb=vec3(float(px.x)/255.);
"""+s[b:]
    return s

class Field:
    def __init__(self,base):
        self.base=base
        for n in CUBES:base.STAGE_TABLE[n]=(False,False,None,"grass_block",False,18000)
    def __getattr__(self,key):return getattr(self.base,key)
    def self_test(self,stages):assert stages==list(CUBES)
    def geometry(self,names):
        return dict(camera=POSE,torch=TORCH,blocks=CUBES,floorY=151,time=18000,stages=names)
    def datapack(self,names):
        self.self_test(names)
        files=self.base.datapack(names)
        for i,n in enumerate(names):
            key=f"data/animal/function/s{i}.mcfunction"
            stage=files[key]
            mark=f"say AQLAVA_BEGIN_{n}_END"
            xyz=" ".join(map(str,CUBES[n]))
            cmds=[f"gamemode spectator {self.PLAYER}",f"tp {self.PLAYER} {POSE}",
                  "fill 403 151 -413 410 155 -405 air","fill 403 150 -413 410 150 -405 grass_block",
                  f"setblock {TORCH} torch",f"setblock {xyz} birch_log",mark]
            files[key]=replace(stage,mark,"\n".join(cmds))
            checks=[f"positioned 406.5 156 -409.5 if entity @a[name={self.PLAYER},gamemode=spectator,distance=..0.04,x_rotation=88.95..89.05,y_rotation=-0.05..0.05]",
                    f"if block {TORCH} torch","if block 405 150 -409 grass_block","if block 406 155 -409 air"]
            for tag,cell in CUBES.items(): checks.append("if block "+" ".join(map(str,cell))+(" birch_log" if tag==n else " air"))
            for pre in ("v","e"):
                key=f"data/animal/function/{pre}{i}.mcfunction"
                lines=files[key].splitlines()
                target=next(k for k,v in enumerate(lines) if v.startswith("execute if score #t"))
                lines[target]="execute if score #t aq_room matches 18000 "+" ".join(checks)+" run scoreboard players set #ok aq_room 1"
                files[key]="\n".join(lines)+"\n"
        return files

if __name__=="__main__":
    if sys.argv[1]=="build": print(build(WORK/NAME,screen));raise SystemExit()
    assert guarded.sha(WORK/NAME)==sys.argv[1]
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(CUBES),
               glcache=str(guarded.BUILD/"driver-cache"),**{"period-ticks":"200","shot-gap":".15",
               "compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(WORK/NAME,"one-block-at-night","off",fixed,HERE,Field)
