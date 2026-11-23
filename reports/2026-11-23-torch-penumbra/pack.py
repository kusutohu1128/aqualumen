"""Build a private finite-source experiment on the exact preview 12 archive."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / "build/torch-penumbra"
BASE = ROOT / "dist/Aqualumen-1.9.0-preview.12.zip"
CHECKSUM = "be935f1b5b30b581e5a3539c2031bd1d0d5fcf26647c28fd4bde42567c954ab2"


def edit(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


def build(rim=False):
    assert sha256(BASE.read_bytes()).hexdigest() == CHECKSUM
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / ("Aqualumen-Torch-Rim.zip" if rim else "Aqualumen-Torch-Penumbra.zip")
    with ZipFile(BASE) as prev, ZipFile(path, "w") as out:
        for item in prev.infolist():
            data = prev.read(item)
            name = item.filename
            if name == "shaders/shaders.properties":
                data = edit(data, b"float false false 512 2048\n", b"float false false 512 2112\n")
            if name == "shaders/lib/local_light_grid.glsl":
                marker = b"vec3 lampOffset("
                data = edit(data,marker,b"ivec2 lampBrickAddress(ivec3 brick) { return ivec2(0,2048)+lampAddress(lampLinear(brick,32),512); }\n"+marker)
            if name == "shaders/shadowcomp1.csh":
                marker=b"    for(int i=0;i<8;i++) {\n        ivec3 cell=first+lampUnpack(i,2);"
                data=edit(data,marker,b"    uint masks=0u;\n"+marker)
                marker=b"        if(hasLavaStorage &&"
                data=edit(data,marker,b"""        uint shape=word&63u;
        if(shape!=0u) masks|=1u<<uint(i+(shape==1u?0:8));
"""+marker)
                marker=b"    if(gl_LocalInvocationIndex!=0u) return;"
                data=edit(data,marker,b"    imageStore(lampFieldImage,lampBrickAddress(first/2),vec4(float(masks)));\n"+marker)
            if name == "shaders/lib/local_lighting.glsl":
                marker=b"// Fixed quadrature"
                data=edit(data,marker,(HERE/("rim.glsl" if rim else "box_source.glsl")).read_bytes()+(HERE/"brick_disk.glsl").read_bytes()+marker)
                marker=b"    // Most rays only need"
                data=edit(data,marker,b"""    // The segment sampler already ignores the holder for carried lights.
    // A frame containing only its own triangles has no eligible entity caster.
    bool testBody=occluders.entityTest;
#if ENTITY_LIGHT_SHADOWS == 1
    if(testBody && (carried || entityReceiverIsHand))
        testBody=texelFetch(aqualumenEntityMeta,ivec2(entityMetaTriangles,0),0).r
              !=texelFetch(aqualumenEntityMeta,ivec2(entityMetaSelf,0),0).r;
#endif
    if(!testBody && !occluders.leafVolume) {
        float area=simpleBrickVisibility(start,centre,u,v,carried);
        if(area>=0.) return vec3(area);
    }
"""+marker)
            out.writestr(item,data)
    return path


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--rim",action="store_true")
    pack=build(parser.parse_args().rim)
    print(sha256(pack.read_bytes()).hexdigest(),pack)
