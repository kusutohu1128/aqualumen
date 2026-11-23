"""Compare both lighting programs in the same frame with the coloured pane behind the eye."""
from zipfile import ZipFile
import json
import numpy as np
from PIL import Image
from screen_trials import HERE,ROOT,PACK,DIGEST,guarded,SelectiveRoom
from window_room import LAYOUT
STAGES=("front","behind-a","behind-b","behind-c","behind-cow")
CAMERAS={s:f"{x:.4f} 151 -410.48 178 7" for s,x in zip(STAGES[1:],(406.4320,406.4324,406.4328,406.4328))}
for s in STAGES: LAYOUT[s]=dict(LAYOUT["red-ew"])

class RearRoom(SelectiveRoom):
    def __init__(self,base):
        super().__init__(base)
        base.STAGE_TABLE["behind-cow"]=base.STAGE_TABLE["red-cow"]
    def geometry(self,names):
        g=super().geometry(names)
        g["stageCameras"].update(CAMERAS)
        return g
    def datapack(self,names):
        files=super().datapack(names)
        for i,s in enumerate(names):
            if s=="front":continue
            pos=" ".join(CAMERAS[s].split()[:3])
            for phase in "sve":
                k=f"data/animal/function/{phase}{i}.mcfunction"
                txt=files[k]
                assert txt.count("409.48 151 -405.95")==1
                txt=txt.replace("409.48 151 -405.95",pos)
                if phase=="s":
                    assert "153.8 7" in txt
                    txt=txt.replace("153.8 7","178 7")
                else:
                    assert "y_rotation=153.75..153.85" in txt
                    txt=txt.replace("y_rotation=153.75..153.85","y_rotation=177.95..178.05")
                files[k]=txt
        return files

def make_pack():
    assert guarded.sha(PACK)==DIGEST
    with ZipFile(PACK) as source: data={k:source.read(k) for k in source.namelist()}
    prop="shaders/shaders.properties"
    data[prop]+=b"flip.deferred.colortex1=false\n"+''.join(f"flip.deferred1.colortex{n}=false\n" for n in (0,4,8,10,14)).encode()
    prep="shaders/prepare.fsh"
    data[prep]=data[prep].replace(b"const int colortex0Format",b"const int colortex1Format = RGBA32F;\nconst int colortex0Format")
    k="shaders/lib/window_scene.glsl"
    original=data[k].decode().replace("RENDERTARGETS:0,4,8,10,14","RENDERTARGETS:0,4,8,10,14,1")
    end=original.rindex("}")
    data[k]=(original[:end]+"""
#ifdef WINDOW_ROUTE
    gl_FragData[5]=vec4(color,2.);
#else
    gl_FragData[5]=vec4(color,1.);
#endif
}
""").encode()
    lighting=data["shaders/lib/local_lighting.glsl"].decode()
    call="return windowDisk(cell,slot,start,centre,u,v,radius);"
    assert lighting.count(call)==1
    pair="if(pairMask!=0 && (flags&pairMask)==pairMask) {"
    assert lighting.count(pair)==1
    lighting=lighting.replace(pair,pair+" expectedWindow=true;")
    lighting=lighting.replace(call,"{ vec3 filterRGB=windowDisk(cell,slot,start,centre,u,v,radius); colouredWindow=colouredWindow || any(lessThan(filterRGB,vec3(.985))); return filterRGB; }")
    data["shaders/lib/reference_lighting.glsl"]=("bool expectedWindow=false,colouredWindow=false;\n"+lighting).encode()
    final=data["shaders/final.fsh"].decode()
    tone=final[final.index("#define MIDTONE_CONTRAST"):final.index("const float voxelDistance")]+final[final.index("vec3 tone("):final.index("void main() {")]
    reference=original[:end].replace('"/lib/local_lighting.glsl"','"/lib/reference_lighting.glsl"')
    reference=reference.replace("void main() {","uniform sampler2D colortex1;\n"+tone+"\nvoid main() {")
    reference += """
    vec4 tested=texelFetch(colortex1,pixel,0);
    vec3 a=round(255.*pow(tone(color,1.),vec3(1./2.2)));
    vec3 b=round(255.*pow(tone(tested.rgb,1.),vec3(1./2.2)));
    vec3 diff=abs(a-b);
    bool valid=tested.a==1. || tested.a==2.;
    bool miss=!valid || (expectedWindow && tested.a!=2.);
    gl_FragData[5]=vec4(miss?255.:(tested.a==2.?64.:32.),colouredWindow?255.:0.,max(diff.r,max(diff.g,diff.b)),tested.a);
}
"""
    data["shaders/deferred2.fsh"]=("#version 330 compatibility\n#define WINDOW_ROUTE\n"+reference).encode()
    data["shaders/deferred2.vsh"]=b'#version 330 compatibility\n#include "/lib/fullscreen.vsh.glsl"\n'
    data["shaders/final.fsh"]=b"""#version 330 compatibility
uniform sampler2D colortex1;
void main(){gl_FragColor=vec4(texelFetch(colortex1,ivec2(gl_FragCoord.xy),0).rgb/255.,1.);}
"""
    import sys
    sys.path.insert(0,str(ROOT/"tools"))
    from land_shadow_pack import zip_bytes,ArchiveEntry
    raw=zip_bytes(tuple(ArchiveEntry(k,v) for k,v in sorted(data.items())))
    p=ROOT/"build/window-tiles/Aqualumen-Behind-Window-Records.zip"
    if p.exists():assert p.read_bytes()==raw
    else:p.write_bytes(raw)
    return p

def run(label):
    pack=make_pack();folder=HERE/label
    assert not folder.exists()
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(STAGES),glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"240","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:guarded.launch(pack,label,"off",fixed,HERE,RearRoom)
    except SystemExit as exc:
        if exc.code:raise
    receipt=json.loads((folder/"complete.json").read_text())
    assert receipt["complete"] and receipt["packSha256"]==guarded.sha(pack)
    rows={}
    for s in STAGES:
        p=folder/(s+"-ingame.png")
        assert guarded.sha(p)==receipt["screenshots"][s]["ingame"]
        pixels=np.asarray(Image.open(p).convert("RGB"))
        # The F2 screenshot may include a transient system toast in the corner.
        coded=np.isin(pixels[:,:,0],(32,64,255))&((pixels[:,:,1]==0)|(pixels[:,:,1]==255))
        assert coded.mean()>.998
        red,green,blue=pixels[coded].T
        rows[s]=dict(pixels=int(coded.sum()),omitted=int((red==255).sum()),tinted=int((green==255).sum()),
                     differing=int((blue>0).sum()),aboveOne=int((blue>1).sum()),maximumBytes=int(blue.max()),
                     ordinaryPixels=int((red==32).sum()),windowPixels=int((red==64).sum()),
                     aboveOneOrdinary=int(((red==32)&(blue>1)).sum()),aboveOneWindow=int(((red==64)&(blue>1)).sum()))
    (folder/"comparison.json").write_text(json.dumps(rows,indent=2)+"\n")
    assert not any(v["omitted"] for v in rows.values())
    assert min(rows[s]["tinted"] for s in ("behind-a","behind-b","behind-c"))>100
if __name__=="__main__":
    import sys
    run(sys.argv[1])
