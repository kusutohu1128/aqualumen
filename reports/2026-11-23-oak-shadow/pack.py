"""Build the private finite-lamp candidate from the exact preview 10 archive."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
import hashlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/"dist/Aqualumen-1.9.0-preview.10.zip"
WORK=ROOT/"build/oak-shadow"
PACK=WORK/"Aqualumen-Solid-Disk.zip"
ADD="shaders/lib/solid_disk.glsl"

def source(slabs,tangent=False):
    code=(HERE/"study"/ADD).read_bytes()
    if not slabs: return code
    code=code[:code.index(b"// A small axis-aligned box")]
    for old,new in ((b"cubeDiskVisibility(",b"boxDiskVisibility("),
                    (b"ivec3 cell) {",b"ivec3 cell,vec3 size) {"),
                    (b"base+.5,l",b"base+.5*size,l"),
                    (b"dot(abs(l),vec3(1.))",b"dot(abs(l),size)"),
                    (b"base+vec3(i&1,(i>>1)&1,(i>>2)&1)",b"base+size*vec3(i&1,(i>>1)&1,(i>>2)&1)"),
                    (b"base[axis]>=-1.",b"base[axis]>=-size[axis]")):
        assert code.count(old)==1
        code=code.replace(old,new)
    body=(HERE/"study2/slabs.glsl").read_bytes()
    if tangent:
        # Treat a subpixel sliver consistently when resolving two independent
        # silhouettes. The negative sentinel still requests the original tracer.
        old=b"if(s1==0. || s2==0.) return 0.;"
        assert body.count(old)==1
        body=body.replace(old,b"if((s1>=0. && s1<=1e-5) || (s2>=0. && s2<=1e-5)) return 0.;")
        for term in (b"s1",b"s2"):
            assert body.count(term+b"==1.")==1
            body=body.replace(term+b"==1.",term+b">=1.-1e-5")
    return code+body


def build(slabs=False,tangent=False):
    assert not tangent or slabs
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()=="a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9"
    WORK.mkdir(parents=True,exist_ok=True)
    output=WORK/("Aqualumen-Solid-Tangent.zip" if tangent else "Aqualumen-Solid-Slabs.zip") if slabs else PACK
    with ZipFile(BASE) as old, ZipFile(output,"w") as new:
        for item in old.infolist():
            body=old.read(item)
            if item.filename=="shaders/lib/local_lighting.glsl":
                include=b'#include "/lib/leaf_disk.glsl"'
                marker=b'    // Most rays only need'
                assert body.count(include)==body.count(marker)==1
                body=body.replace(include,include+b'\n#include "/lib/solid_disk.glsl"')
                body=body.replace(marker,b'''    if(!carried && !occluders.entityTest && occluders.leafCell.x<0) {
        float visible=simpleSolidVisibility(start,centre,l,u,v);
        if(visible>=0.) return vec3(visible);
    }
'''+marker)
            new.writestr(item,body)
        info=ZipInfo(ADD,old.getinfo("shaders/lib/leaf_disk.glsl").date_time)
        info.external_attr=0o100644<<16
        new.writestr(info,source(slabs,tangent),compress_type=ZIP_DEFLATED)
    with ZipFile(output) as new:
        assert new.testzip() is None
        new.extractall(WORK/("tangent" if tangent else "slabs" if slabs else "candidate"))
    print(output,hashlib.sha256(output.read_bytes()).hexdigest())

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--slabs",action="store_true")
    parser.add_argument("--tangent",action="store_true")
    args=parser.parse_args()
    build(args.slabs or args.tangent,args.tangent)
