"""Exclude only cells disjoint from the entire one-metre receiver/emitter hull."""
from pack import HERE, WORK, NAME, build, replace
from continuous import transform
NORMAL=NAME.replace("-Study","-Hull")
METER=NAME.replace("-Study","-Hull-Meter")

def changed(name,s,d):
    s=transform(name,s,d)
    if name=="shaders/lib/local_lighting.glsl":
        s=replace(s,"        int slot;\n        int flags=flagsForTorch(neighbour", """        // An opaque neighbour contains no continuation of this receiver face.
        // A perpendicular wall meets it at a real corner, not a solver seam.
        if(lampInGrid(neighbour) && (int(texelFetch(aqualumenLightField,lampCellAddress(neighbour),0).r)&63)==1) continue;
        int slot;
        int flags=flagsForTorch(neighbour""")
    if name=="shaders/shadowcomp6.csh":
        s=replace(s,"int classifyTorchPath(ivec3 lo,ivec3 hi,ivec3 sourceCell,bool allowSolid)",
                  (HERE/"swept.glsl").read_text()+"\nint classifyTorchPath(ivec3 lo,ivec3 hi,ivec3 sourceCell,bool allowSolid,bool tight,ivec3 receiver,vec3 source)")
        s=replace(s,"        if(((word>>8)&clip)!=0) return -1;","""        if(tight) {
            int remaining=(word|(word>>8))&clip;
            clip=0;
            while(remaining!=0) {
                int index=findLSB(remaining);
                remaining&=remaining-1;
                if(sweptTorchCell(base+lampUnpack(index,2),receiver,source)) clip|=1<<index;
            }
        }
        if(((word>>8)&clip)!=0) return -1;""")
        s=replace(s,"int geometry=classifyTorchPath(lo,hi,ivec3(floor(source.xyz)),kind>=1 && kind<=10);","""bool torch=kind>=1 && kind<=10;
            ivec3 sourceCell=ivec3(floor(source.xyz));
            int geometry=classifyTorchPath(lo,hi,sourceCell,torch,false,cell,source.xyz);
            if(geometry<0 && torch) {
                int tight=classifyTorchPath(lo,hi,sourceCell,true,true,cell,source.xyz);
                if(tight>0) geometry=tight;
            }""")
    return s
if __name__=="__main__":
    for d,p in ((False,NORMAL),(True,METER)):
        print(p,build(WORK/p,lambda n,s:changed(n,s,d)))
