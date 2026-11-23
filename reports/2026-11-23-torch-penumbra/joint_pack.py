"""Hand-held finite-source trial, including conditional transmission through living casters."""
from copy import copy
from hashlib import sha256
from zipfile import ZipFile
from pack import HERE, WORK, BASE, edit, build


def build_joint():
    # Preserve the shared brick producer and exact preview 12 baseline.
    rim=build(rim=True)
    path=WORK/"Aqualumen-Hand-Penumbra.zip"
    with ZipFile(rim) as src,ZipFile(path,"w") as dst:
        for info in src.infolist():
            data=src.read(info)
            if info.filename=="shaders/lib/local_lighting.glsl":
                code=data.decode()
                code=edit(code,"vec3 delta,vec3 u,vec3 v) {\n    // A ray leaving",
                          "vec3 delta,vec3 u,vec3 v,out vec2 witness) {\n    float nearest=1.; witness=vec2(0);\n    // A ray leaving")
                code=edit(code,"if(abs(d)<1e-7) d=1e-7;","if(d<nearest) { nearest=d; witness=-n*(.5+.5*d); }\n        if(abs(d)<1e-7) d=1e-7;")
                code=edit(code,"vec3 u, vec3 v, bool carried) {","vec3 u, vec3 v, bool carried, out bool materials, out vec3 boxLo, out vec3 boxHi, out vec2 witness) {\n    materials=false; boxLo=vec3(0); boxHi=vec3(0); witness=vec2(0);")
                code=edit(code,"if((word&(1<<bit))==0) return -1.;","if((word&(1<<bit))==0) { materials=true; continue; }")
                code=edit(code,"return boxSourceVisibility(vec3(lo)-a,vec3(hi+1)-a,delta,u,v);",
                          "boxLo=vec3(lo)-a; boxHi=vec3(hi+1)-a;\n    return boxSourceVisibility(boxLo,boxHi,delta,u,v,witness);")
                code=edit(code,"// Fixed quadrature",(HERE/"joint.glsl").read_text()+"\n// Fixed quadrature")
                begin=code.index("    // The segment sampler already ignores")
                end=code.index("    // Most rays only need",begin)
                code=code[:begin]+"""    if(carried && !occluders.leafVolume) {
        bool materials; vec3 lo,hi; vec2 witness;
        float area=simpleBrickVisibility(start,centre,u,v,carried,materials,lo,hi,witness);
        if(area>=0.) {
            bool body=occluders.entityTest;
#if ENTITY_LIGHT_SHADOWS == 1
            if(body) body=texelFetch(aqualumenEntityMeta,ivec2(entityMetaTriangles,0),0).r
                       !=texelFetch(aqualumenEntityMeta,ivec2(entityMetaSelf,0),0).r;
#endif
            if(area==0. || (!body && !materials)) return vec3(area);
            if(body || area<1.) {
                occluders.entityTest=body;
                return jointDiskSamples(start,centre,u,v,lo,hi,area,witness,occluders);
            }
        }
    }
"""+code[end:]
                data=code.encode()
            dst.writestr(info,data)
    return path


if __name__=="__main__":
    pack=build_joint()
    print(sha256(pack.read_bytes()).hexdigest(),pack)
