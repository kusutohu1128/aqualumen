"""Match disk quadrature across exact-shadow and traced terrain near cache boundaries."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
import math
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORK=ROOT/"build/torch-shadow-integral"
PACKS=(("Aqualumen-Torch-caps.zip","c32be3d49b7ad0ac80697b994861e74ee651e36df8f2b80f393cb12c2709f293"),
       ("Aqualumen-Torch-caps-meter.zip","ad45a2a3e17cfa3e2d0d14bdc51616b6e3bf0eeae7cc60165635bd926a206551"))


def shader(source,taps):
    # Equal-area sunflower disk, fixed relative to the light and surface.
    points=[]
    for i in range(taps):
        r=math.sqrt((i+.5)/taps);a=i*2.39996323+.417
        points.append(f"vec2({r*math.cos(a):.9f},{r*math.sin(a):.9f})")
    pattern=f"const int terrainDiskCount={taps};\nconst vec2 terrainDisk[{taps}]=vec2[{taps}](\n    "+",\n    ".join(points)+");\n\n"
    insert=source.index("bool crossesPair(")
    source=source[:insert]+pattern+source[insert:]
    p=source.index("    float pilot=float(!crossesPair(")
    q=source.index("\n}",p)
    source=source[:p]+"""    float clearSamples=0.;
    for(int i=0;i<terrainDiskCount;i++) {
        vec2 tap=terrainDisk[i];
        if(!crossesPair(lo,hi,loB,hiB,delta+tap.x*u+tap.y*v,pair)) clearSamples+=1.;
    }
    return mix(clearSamples/float(terrainDiskCount),area,weight);"""+source[q:]
    marker="    bool leafDisk=false;"
    assert source.count(marker)==1
    source=source.replace(marker,"    bool terrainDiskActive=false;\n"+marker)
    marker="        if(i<3) {"
    assert source.count(marker)==1
    source=source.replace(marker,"""#ifdef OPEN_TERRAIN_PATH
        if(terrainDiskActive) disk=terrainDisk[i-3];
        else
#endif
"""+marker)
    p=source.index("        if(i==2 && !occluders.entityTest)")
    q=source.index("\n        }\n    }\n    return sum/float",p)
    source=source[:q]+"""
#ifdef OPEN_TERRAIN_PATH
            if(count==3 && !carried && !occluders.leafVolume) {
                terrainDiskActive=true;
                count=3+terrainDiskCount;
                sum=vec3(0.);
            }
#endif"""+source[q:]
    return source.replace("sum/float(leafDisk?count-3:count)","sum/float((leafDisk || terrainDiskActive)?count-3:count)")


def build(taps,adaptive=False):
    for name,digest in PACKS:
        base=WORK/name
        assert sha256(base.read_bytes()).hexdigest()==digest
        dst=WORK/name.replace("caps",("adaptive" if adaptive else "motion")+str(taps))
        with ZipFile(base) as a,ZipFile(dst,"w") as b:
            for item in a.infolist():
                data=a.read(item)
                if item.filename=="shaders/lib/local_lighting.glsl":
                    text=shader(data.decode(),taps)
                    if adaptive:
                        marker="if(count==3 && !carried && !occluders.leafVolume)"
                        assert text.count(marker)==1
                        text=text.replace(marker,"if(count==3 && !carried && !occluders.leafVolume && (lampSolidHit.w>0. || most-least>.01))")
                    data=text.encode()
                b.writestr(item,data)
        print(dst,sha256(dst.read_bytes()).hexdigest())


if __name__=="__main__":build(int(sys.argv[1]),sys.argv[2:]==["--adaptive"])
