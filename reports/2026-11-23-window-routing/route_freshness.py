"""Stamp nine pixels of all five deferred outputs. Count all stale frames on the GPU."""
import json
from zipfile import ZipFile
from PIL import Image
from route_room import HERE, ROOT, ChallengeRoom, guarded
from selective_room import PACK, DIGEST, SelectiveRoom

STAGES = ("air", "red-ew", "blue-ew", "unlit-pane", "distant-pane", "post", "clear-again")
SLOTS = ("ordinaryFrames", "paneFrames", "routeChanges", "errorFrames", "target0Errors", "target4Errors",
         "target8Errors", "target10Errors", "target14Errors", "route", "lastFrame", "discontinuousFrames", "presentPaneTiles")
PIXELS = """
ivec2 routePixel(int k,ivec2 size) {
    return size*ivec2(1+3*(k%3),1+3*(k/3))/8;
}
"""

def diagnostic():
    assert guarded.sha(PACK) == DIGEST
    with ZipFile(PACK) as source:
        contents = {name: source.read(name).decode() for name in source.namelist()}
    header = "#version 430 compatibility\nlayout(local_size_x=1) in;\nconst ivec3 workGroups=ivec3(1,1,1);\n"
    storage = "layout(r32f) uniform image2D lampFieldImage;\n"
    contents["shaders/setup3.csh"] = header + storage + "void main(){ for(int i=0;i<13;i++) imageStore(lampFieldImage,ivec2(i==12?84:52+i,2688),vec4(0)); }\n"
    scene = "shaders/lib/window_scene.glsl"
    contents[scene] = contents[scene].replace("void main() {", "uniform int frameCounter;\n"+PIXELS+"void main() {")
    end = contents[scene].rindex("}")
    writes = "\n".join(f"            gl_FragData[{i}].r=mark+{i}.;" for i in range(5))
    contents[scene] = contents[scene][:end]+"""
    for(int k=0;k<9;k++) {
        if(all(equal(ivec2(gl_FragCoord.xy),routePixel(k,ivec2(viewWidth,viewHeight))))) {
            float mark=1.+float(frameCounter%127)*8.;
#ifdef WINDOW_ROUTE
            mark+=1024.;
#endif
"""+writes+"\n        }\n    }\n}\n"
    targets = (0, 4, 8, 10, 14)
    textures = "".join(f"uniform sampler2D colortex{t};\n" for t in targets)
    reads = "".join(f"bad[{i}]=bad[{i}]||texelFetch(colortex{t},p,0).r!=mark+{i}.;\n" for i,t in enumerate(targets))
    contents["shaders/deferred2.csh"] = header+storage+textures+PIXELS+"""
#include "/lib/window_route_address.glsl"
uniform int frameCounter;
uint getSlot(int i){return uint(imageLoad(lampFieldImage,ivec2(i==12?84:52+i,2688)).r);}
void setSlot(int i,uint v){imageStore(lampFieldImage,ivec2(i==12?84:52+i,2688),vec4(float(v)));}
void main(){
    uint tiles=0u;
    for(int row=0;row<512;row++) {
        int index=row*32+16;
        tiles+=uint((int(imageLoad(lampFieldImage,ivec2(index%512,2688+index/512)).r)&2)!=0);
    }
    setSlot(12,tiles);
    int route=int(imageLoad(lampFieldImage,windowRouteAddress).r>.5);
    uint previous=getSlot(9);
    int frame=frameCounter%127;
    if(previous>0u && getSlot(10)!=uint((frame+126)%127)) setSlot(11,getSlot(11)+1u);
    if(previous>0u && previous!=uint(route+1)) setSlot(2,getSlot(2)+1u);
    setSlot(9,uint(route+1)); setSlot(10,uint(frame)); setSlot(route,getSlot(route)+1u);
    float mark=float(1+frame*8+route*1024);
    bool bad[5]=bool[5](false,false,false,false,false);
    for(int k=0;k<9;k++){
        ivec2 p=routePixel(k,textureSize(colortex0,0));
"""+reads+"""
    }
    bool error=false;
    for(int i=0;i<5;i++) if(bad[i]){setSlot(4+i,getSlot(4+i)+1u);error=true;}
    if(error) setSlot(3,getSlot(3)+1u);
}
"""
    final = "shaders/final.fsh"
    # A header and little-endian 24-bit counters, encoded after tone mapping.
    contents[final] = contents[final].replace("void main() {", """uniform sampler2D aqualumenLightField;
void main() {
    ivec2 codePos=ivec2(gl_FragCoord.xy);
    if(codePos.y<8 && codePos.x<112) {
        int n=codePos.x/8;
        uint v=n==0?0x213a6du:uint(texelFetch(aqualumenLightField,ivec2(n==13?84:51+n,2688),0).r);
        gl_FragColor=vec4(vec3(uvec3(v,v>>8,v>>16)&uvec3(255))/255.,1.);
        return;
    }
""")
    dest=ROOT/"build/window-routing/Aqualumen-Lit-Route-Freshness.zip"
    import sys
    sys.path.insert(0,str(ROOT/"tools"))
    from land_shadow_pack import ArchiveEntry, zip_bytes
    data=zip_bytes(tuple(ArchiveEntry(k, v.encode()) for k,v in sorted(contents.items())))
    if dest.exists(): assert dest.read_bytes()==data
    else: dest.write_bytes(data)
    return dest

def run(label):
    pack=diagnostic()
    assert not (HERE/label).exists()
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(STAGES),glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"210","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:
        guarded.launch(pack,label,"off",fixed,HERE,SelectiveRoom)
    except SystemExit as exc:
        if exc.code: raise
    score(label)

def score(label):
    f=HERE/label; rows={}
    complete=json.loads((f/"complete.json").read_text())
    assert complete["complete"] and complete["packSha256"]==guarded.sha(diagnostic())
    for stage in STAGES:
        fn=f/(stage+"-ingame.png")
        assert guarded.sha(fn)==complete["screenshots"][stage]["ingame"]
        im=Image.open(fn).convert("RGB")
        def number(n): return int.from_bytes(bytes(im.getpixel((8*n+3,im.height-4))),"little")
        assert number(0)==0x213a6d
        rows[stage]=dict(zip(SLOTS,(number(i+1) for i in range(len(SLOTS)))))
    (f/"freshness.json").write_text(json.dumps(rows,indent=2)+"\n")
    result=list(rows.values())
    assert [v["route"] for v in result]==[1,2,2,1,1,2,1],rows
    assert all(rows[s]["presentPaneTiles"]>0 for s in ("unlit-pane","distant-pane","red-ew"))
    assert all(r["errorFrames"]==0 and r["discontinuousFrames"]==0 for r in result)
    assert result[-1]["routeChanges"]>=4 and min(result[-1][k] for k in SLOTS[:2])>20

if __name__=="__main__":
    import sys
    if sys.argv[1]=="build": print(diagnostic())
    elif sys.argv[1]=="score": score(sys.argv[2])
    else: run(sys.argv[1])
