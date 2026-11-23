"""Paired output of both complete final passes from a single HDR frame in the guarded TEST world."""
from pathlib import Path
import sys

from diffuse_meter import DIST, FLEX, WORK
from make_pack import ROOT, HERE, SHIP, ZipFile, sha256
sys.path.insert(0, str(HERE.parent / "2026-11-23-torch-density"))
from measure_density import guarded, World, PREFIX

STAGES = {"shore-evening": (11900,90.,-4.), "shore-day": (7800,90.,9.), "ore-light": (17000,0.,-5.)}
POSE="157.5 63 349.5"
SAMPLES={"157 65 353":"redstone_ore[lit=true]", "158 65 353":"glowstone"}

def pair_pack(pack=DIST):
    assert sha256(DIST.read_bytes()).hexdigest()=="e5964a858e8c6f671c84cdea6b71c905b58b13a8cef2ca5f655adee2ca8966b9"
    assert pack in (DIST,FLEX)
    path=WORK/("Aqualumen-Midtones-Pair.zip" if pack==FLEX else "Aqualumen-Diffuse-Pair.zip")
    with ZipFile(pack) as new, ZipFile(SHIP) as old, ZipFile(path,"w") as result:
        for item in new.infolist():
            data=new.read(item)
            if item.filename=="shaders/final.fsh":
                shader=data.decode()
                orig=old.read(item.filename).decode()
                old_tone=orig[orig.index("vec3 tone("):orig.index("void main()")].replace("vec3 tone(","vec3 previousTone(")
                prefix,body=shader.split("void main() {")
                assert body.count("gl_FragColor=")==1
                body=body.replace("gl_FragColor=","return ").replace("texcoord","uv")
                old_body=body.replace("tone(","previousTone(")
                data=(prefix+old_tone+"vec4 previousFrame(vec2 uv) {"+old_body+
                      "vec4 candidateFrame(vec2 uv) {"+body+"""
void main() {
    ivec2 size=textureSize(colortex0,0);
    ivec2 dst=ivec2(gl_FragCoord.xy);
    ivec2 pos=(dst%(size/2))*2+ivec2(1);
    vec2 uv=(vec2(pos)+.5)/vec2(size);
    if(dst.y>=size.y/2) {
        gl_FragColor=dst.x<size.x/2?previousFrame(uv):candidateFrame(uv);
        return;
    }
    float depth=texelFetch(depthtex0,pos,0).r;
    float opaque=texelFetch(depthtex1,pos,0).r;
    if(dst.x<size.x/2) {
        vec3 ray=normalize(mat3(gbufferModelViewInverse)*viewPosition(uv,depth));
        bool sky=depth>=.999999;
        gl_FragColor=vec4(float(sky),float(depth<opaque),
                          float(sky && dot(ray,sunDirection())>cos(radians(.24))),1.);
    } else {
        vec3 c=max(texelFetch(colortex0,pos,0).rgb*exposureScale(),vec3(0.));
        gl_FragColor=vec4(clamp((log2(max(c,vec3(exp2(-12.))))+12.)/24.,0.,1.),1.);
    }
}
""").encode()
            result.writestr(item,data)
    return path


class Shore:
    def __init__(self, rooms):
        self.rooms=rooms
        self.STAGE_TABLE=STAGES
    def __getattr__(self,key):
        return getattr(self.rooms,key)
    def self_test(self,names):
        assert names in (list(STAGES),["shore-evening"])
        w=World()
        for cell in SAMPLES:
            assert w.name(*map(int,cell.split()))=="minecraft:air"
        assert w.name(157,62,349)=="minecraft:sand" and w.name(130,62,349)=="minecraft:water" and w.unchanged()
    def geometry(self,names):
        return dict(stages=STAGES,feet=POSE,placedOnlyDuringOreStage=SAMPLES,
                    upperLeft="Rows",upperRight="Diffuse",lowerLeft="sky, foreground translucent, solar centre",lowerRight="log2 exposed RGB from -12 to +12")
    def datapack(self,names):
        self.self_test(names)
        files=self.rooms.datapack(["day-white"])
        for i,stage in enumerate(names):
            time,yaw,pitch=STAGES[stage]
            def put(name,lines):
                files[f"{PREFIX}{name}{i}.mcfunction"]="\n".join(lines)+"\n"
            put("s",[f"gamemode spectator {self.PLAYER}",f"tp {self.PLAYER} {POSE} {yaw} {pitch}",
                 f"time set {time}",f"say AQLAVA_BEGIN_{stage}_END",f"schedule function animal:p{i} 50t replace",
                 f"schedule function animal:v{i} {self.READY_AT}t replace",f"schedule function animal:e{i} {self.STILL_AT}t replace",
                 f"schedule function animal:s{(i+1)%len(names)} {self.PERIOD}t replace"])
            put("p",[f"execute if block {cell} air run setblock {cell} {material}" for cell,material in SAMPLES.items()] if stage=="ore-light" else ["# natural shore"])
            checks=["scoreboard players set #ok aq_room 1","execute store result score #t aq_room run time query daytime",
                    f"execute unless score #t aq_room matches {time} run scoreboard players set #ok aq_room 0",
                    f"execute positioned {POSE} unless entity @a[name={self.PLAYER},gamemode=spectator,distance=..0.04,x_rotation={pitch-.05}..{pitch+.05},y_rotation={yaw-.05}..{yaw+.05}] run scoreboard players set #ok aq_room 0",
                    "execute unless block 130 62 349 water run scoreboard players set #ok aq_room 0"]
            for c, block in SAMPLES.items():
                checks.append(f"execute unless block {c} {block if stage=='ore-light' else 'air'} run scoreboard players set #ok aq_room 0")
            for fn,yes,no in (("v","READY","FAIL"),("e","STILL","DRIFT")):
                lines=checks[:]
                if fn=="e" and stage=="ore-light":
                    for c,block in SAMPLES.items():
                        lines.extend([f"execute if block {c} {block} run setblock {c} air", f"execute unless block {c} air run scoreboard players set #ok aq_room 0"])
                put(fn,lines+[f"execute if score #ok aq_room matches 1 run say AQLAVA_{yes}_{stage}_END",
                              f"execute unless score #ok aq_room matches 1 run say AQLAVA_{no}_{stage}_END"])
        return files

if __name__=="__main__":
    pack=pair_pack(FLEX if "--balanced" in sys.argv else DIST)
    factory=Shore(None)
    factory.self_test(list(STAGES))
    if "--build-only" in sys.argv:
        print(pack.name,sha256(pack.read_bytes()).hexdigest())
    else:
        params=dict(backend="vgl",size="1600x900",stages=",".join(STAGES),settle="1",glcache=str(guarded.BUILD/"driver-cache"),
                    **{"period-ticks":"560","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
        guarded.launch(pack,"shore-and-ore-balanced" if "--balanced" in sys.argv else "shore-and-ore","off",params,HERE,Shore)
