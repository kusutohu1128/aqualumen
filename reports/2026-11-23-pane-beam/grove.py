"""Measure both visibility paths in the same shaded grove as the player edits it."""
from io import BytesIO
from pathlib import Path
import sys
from zipfile import ZipFile
from beam_pack import ROOT, WORK, once, meter
from beam_versions import PACKS

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-cell-shadow"))
from moving import Recorder
from room import Grove, guarded, STAGES

EDITS=["shade","torch","trunk","trunk-cut","extinguished"]

class WindowGrove(Grove):
    def self_test(self,names):
        if names!=EDITS: super().self_test(names)

    def geometry(self,names):
        return dict(super().geometry(names),paneRow={"x":[405,407],"y":[151,152],"z":-409})

    def datapack(self,names):
        files=super().datapack(names)
        for i,name in enumerate(names):
            checks=[]
            set_blocks=[]
            for x in (405,406,407):
                tag="red_stained_glass_pane[west="+str(x>405).lower()+",east="+str(x<407).lower()+",north=false,south=false]"
                set_blocks.append(f"fill {x} 151 -409 {x} 152 -409 {tag}")
                # Neighbouring birch logs can change the arm at (406,-409).
                checks.append(f"if block {x} 151 -409 red_stained_glass_pane")
            k=f"data/animal/function/s{i}.mcfunction"
            marker=f"say AQLAVA_BEGIN_{name}_END"
            files[k]=once(files[k],marker,"\n".join(set_blocks+[marker]))
            for prefix in ("e","v"):
                k=f"data/animal/function/{prefix}{i}.mcfunction"
                marker="if block 405 150 -409 grass_block"
                files[k]=once(files[k],marker,marker+" "+" ".join(checks))
        return files

def paired_pack():
    name,digest=PACKS["cells"]
    pack=ROOT/"dist"/f"Aqualumen-{name}.zip"
    assert guarded.sha(pack)==digest
    m=meter(pack,"cells")
    output=BytesIO()
    with ZipFile(m) as src, ZipFile(output,"w") as dst:
        for meta in src.infolist():
            data=src.read(meta)
            if meta.filename=="shaders/lib/local_lighting.glsl":
                s=once(data.decode(),"int beamFastUsed;","int beamFastUsed; bool disableWindowRecord=false;")
                s=once(s,"if(!occluders.entityTest && all(greaterThan(min(fract(start),1.-fract(start)),vec3(.0001))))\n                { beamFastUsed=1;",
                         "if(!disableWindowRecord && !occluders.entityTest && all(greaterThan(min(fract(start),1.-fract(start)),vec3(.0001))))\n                { beamFastUsed=1;")
                line="        vec3 vis=lampVisibility(origin,lamp.xyz,l,radius,carried,occluders);"
                s=once(s,line,"        LampOccluders previousState=occluders;\n"+line)
                line="probeLamps.y=texelFetch(aqualumenLightField,lampCellAddress(ivec3(vec3(406,151,-410)-gridOrigin)),0).r;"
                s=once(s,line,"""int used=beamFastUsed;
            disableWindowRecord=true;
            vec3 control=lampVisibility(origin,lamp.xyz,l,radius,carried,previousState);
            disableWindowRecord=false;
            ivec3 b=ivec3(round(clamp(control,0.,1.)*255.));
            probeLamps.y=float(b.r+256*b.g+65536*b.b);
            beamFastUsed=used;""")
                data=s.encode()
            dst.writestr(meta,data)
    out=WORK/"Aqualumen-Window-Edits-Paired.zip"
    data=output.getvalue()
    if out.exists(): assert out.read_bytes()==data
    else:
        with out.open("xb") as f:f.write(data)
    return out

if __name__=="__main__":
    if "--ordinary" in sys.argv:
        role=sys.argv[-1]; name,digest=PACKS[role]
        pack=ROOT/"dist"/f"Aqualumen-{name}.zip"
        label="grove-"+role+"-ordinary"
        assert guarded.sha(pack)==digest and not (HERE/label).exists()
        fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(EDITS),glcache=str(guarded.BUILD/"driver-cache"),
                   **{"period-ticks":"210","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
        guarded.launch(pack,label,"off",fixed,HERE,WindowGrove)
        sys.exit(0)
    pack=paired_pack()
    if "--build" in sys.argv: print(guarded.sha(pack));sys.exit(0)
    label="grove-edits"
    assert not (HERE/label).exists()
    clips=[Recorder()]
    for old,new in (("shade","lighting"),("torch","planting-trunk"),("home","cutting-trunk"),("trunk-cut","extinguishing")):
        clips.append(Recorder(f"AQLAVA_STILL_{old}_END",new+".mkv",5))
    def prepare(game,out,mods):
        for clip in clips: clip.prepare(game,out,mods)
    def collect(game,out):
        for clip in clips: clip.collect(game,out)
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(STAGES),glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"210","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(pack,label,"off",fixed,HERE,WindowGrove,prepare,collect)
