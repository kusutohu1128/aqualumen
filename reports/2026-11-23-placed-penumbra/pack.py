"""Specialize the finite-emitter area solver for cached, verified static blockers."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORK=ROOT/"build/placed-penumbra"
BASE=ROOT/"dist/Aqualumen-Torch-Cell-Study.zip"
BASE_SHA="e1e06b864967cd61305931d499f71a8f0f07eb66d5696c49eb3a5ecd36903671"
NAME="Aqualumen-Placed-Penumbra-Study.zip"


def replace(text,before,after):
    assert text.count(before)==1,before
    return text.replace(before,after)


def changed(name,shader):
    if name=="shaders/shaders.properties":
        return replace(shader,"float false false 512 2720","float false false 512 8864")
    if name=="shaders/lib/open_cell_layout.glsl":
        return shader+"""
ivec2 torchBoxAddress(ivec3 cell,int slot) {
    return openCellAddress(cell)+ivec2(0,608+slot*512);
}
"""
    if name=="shaders/shadowcomp5.csh":
        begin=shader.index("    // The certificate")
        end=shader.index("    ivec2 prev=",begin)
        shader=shader[:begin]+"    // A solid replaced by leaves must invalidate its cached silhouette.\n    int mask=raw;\n"+shader[end:]
    if name=="shaders/shadowcomp6.csh":
        start=shader.index("bool emptyBox(")
        stop=shader.index("void main()",start)
        shader=shader[:start]+(HERE/"classify.glsl").read_text()+"\n"+shader[stop:]
        shader=replace(shader,"            if(emptyBox(lo,hi)) flags|=1<<i;","""            int geometry=classifyTorchPath(lo,hi,ivec3(floor(source.xyz)),kind>=1 && kind<=10);
            if(geometry==0) flags|=1<<i;
            if(geometry>0) {
                flags|=1<<(i+12);
                imageStore(lampFieldImage,torchBoxAddress(cell,i),vec4(float(geometry)));
            }""")
    if name=="shaders/lib/local_lighting.glsl":
        start=shader.index("bool openLampPath(")
        stop=shader.index("#endif",start)
        shader=shader[:start]+(HERE/"query.glsl").read_text()+shader[stop:]
        start=shader.index("#ifdef OPEN_TERRAIN_PATH\n    if(!carried")
        stop=shader.index("    if(carried && !occluders.leafVolume)",start)
        axis=shader[shader.index("    vec3 axis=abs(l.y)",start):stop]
        shader=shader[:start]+axis+"""#ifdef OPEN_TERRAIN_PATH
    if(!carried && !occluders.leafVolume && !occluders.entityTest) {
        ivec3 cell;
        int flags=torchCellFlags(start,cell);
        if((flags&(1<<openSourceSlot))!=0) return vec3(1);
        if((flags&(1<<(openSourceSlot+12)))!=0)
            return vec3(cachedBoxVisibility(cell,start,centre,u,v,radius));
    }
#endif
"""+shader[stop:]
    return shader


def build(target,extra=None):
    assert sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    target.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(BASE) as src,ZipFile(target,"w") as dst:
        for entry in src.infolist():
            data=src.read(entry)
            if entry.filename.startswith("shaders/"):
                shader=changed(entry.filename,data.decode())
                if extra is not None: shader=extra(entry.filename,shader)
                data=shader.encode()
            dst.writestr(entry,data)
    return sha256(target.read_bytes()).hexdigest()


if __name__=="__main__":
    print(build(WORK/NAME))
