"""Build ordinary and diagnostic variants from the last cow-tested shader pack."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORK=ROOT/"build/mixed-occluders"
METER=ROOT/"build/placed-penumbra/Aqualumen-Placed-Penumbra-Body-Meter.zip"
NORMAL=ROOT/"dist/Aqualumen-Placed-Penumbra-Animal-Study.zip"


def change(s,old,new):
    assert s.count(old)==1,old
    return s.replace(old,new)


def transform(name,s,meter):
    if name=="shaders/shaders.properties":
        return change(s,"float false false 512 8864","float false false 512 15008")
    if name=="shaders/shadowcomp6.csh":
        s=change(s,"int classifyTorchPath(",(HERE/"classify_pair.glsl").read_text()+"\nint classifyTorchPath(")
        s=change(s,"ivec3 receiver,vec3 source) {\n    if(!lampInGrid", "ivec3 receiver,vec3 source,out int second) {\n    second=0;\n    ivec3 points[12];\n    if(!lampInGrid")
        s=change(s,"        solids+=bitCount(bits);","""        if(tight && solids+bitCount(bits)<=12) {
            int writeIndex=solids,remainder=bits;
            while(remainder!=0) {
                points[writeIndex++]=base+lampUnpack(findLSB(remainder),2);
                remainder&=remainder-1;
            }
        }
        solids+=bitCount(bits);""")
        s=change(s,"    if(solids!=size.x*size.y*size.z || any(greaterThan(hi-lo,ivec3(15)))) return -1;","""    if(any(greaterThan(hi-lo,ivec3(15)))) return -1;
    if(solids!=size.x*size.y*size.z) {
        if(tight && solids<=12) return splitSolids(points,solids,occupiedLo,occupiedHi,lo,second);
        return -1;
    }""")
        s=change(s,"            int geometry=classifyTorchPath", "            int second=0;\n            int geometry=classifyTorchPath")
        s=s.replace("cell,source.xyz);","cell,source.xyz,second);")
        s=change(s,"imageStore(lampFieldImage,torchBoxAddress(cell,i),vec4(float(geometry)));","""ivec2 address=torchBoxAddress(cell,i);
                imageStore(lampFieldImage,address,vec4(float(second==0?geometry:-geometry)));
                if(second!=0) imageStore(lampFieldImage,address+ivec2(0,6144),vec4(float(second)));""")
    if name=="shaders/lib/local_lighting.glsl":
        before=s.index("vec3 jointDiskSamples(")
        s=s[:before]+"#ifdef OPEN_TERRAIN_PATH\n"+(HERE/"two_boxes.glsl").read_text()+"\n#endif\n"+s[before:]
        s=change(s,"float visible,vec2 witness,bool carried,inout LampOccluders o)",
                 "float visible,vec2 witness,bool carried,bool pair,vec3 loB,vec3 hiB,inout LampOccluders o)")
        s=change(s,"            p=witness;","""            p=witness;
#ifdef OPEN_TERRAIN_PATH
            if(pair && !openArc(boxLo,boxHi,loB,hiB,source-start,u,v,p)) return vec3(visible);
#endif""")
        s=change(s,"if(j<points && box && rayEntersSolid(boxLo,boxHi,target-start)) continue;","""if(j<points && box && (rayEntersSolid(boxLo,boxHi,target-start) ||
            (pair && rayEntersSolid(loB,hiB,target-start)))) continue;""")
        start=s.index("float continuousBox("); end=s.index("#endif",start)
        s=s[:start]+(HERE/"visible_pair.glsl").read_text()+"\n"+s[end:]
        s=change(s,"vec3 lo,hi; vec2 witness;\n                float visible=", "vec3 lo,hi,loB,hiB; bool pair; vec2 witness;\n                float visible=")
        s=change(s,"radius,lo,hi,witness);","radius,lo,hi,loB,hiB,pair,witness);")
        s=change(s,"lo,hi,visible,witness,false,occluders);","lo,hi,visible,witness,false,pair,loB,hiB,occluders);")
        s=change(s,"lo,hi,area,witness,true,occluders);","lo,hi,area,witness,true,false,vec3(0),vec3(0),occluders);")
        if meter:
            s=change(s,"probeMethod=occluders.entityTest?3:2;","probeMethod=(pair || occluders.entityTest)?3:2;")
    return s


def with_polygon(source):
    start=source.index("float intersectionVisibility(")
    end=source.index("float oneBlocker(",start)
    return source[:start]+(HERE/"overlap_polygon.glsl").read_text()+"\n"+source[end:]

def build(meter,corners=False,polygon=False):
    path=METER if meter else NORMAL
    expected=("8e09c529a48ee717b1c3998ff0fa7bcae38800f0c09a3f21e32ed5598d70f572" if meter else
              "231e3b92831701eea5d7129c65904a63302467b2dc3534a3ffc863c9d6c368ef")
    assert sha256(path.read_bytes()).hexdigest()==expected
    suffix="-Polygon" if polygon else "-Corners" if corners else ""
    output=WORK/("Aqualumen-Two-Opaque-Shadows"+suffix+("-Meter" if meter else "")+".zip")
    with ZipFile(path) as src, ZipFile(output,"w") as dst:
        for entry in src.infolist():
            data=src.read(entry)
            if entry.filename.startswith("shaders/"):
                source=transform(entry.filename,data.decode(),meter)
                if corners and entry.filename=="shaders/lib/local_lighting.glsl":
                    start=source.index("float partialShadowWeight(")
                    end=source.index("void readBox(",start)
                    source=source[:start]+(HERE/"surface_neighbours.glsl").read_text()+"\n"+source[end:]
                if polygon and entry.filename=="shaders/lib/local_lighting.glsl":
                    source=with_polygon(source)
                data=source.encode()
            dst.writestr(entry,data)
    return output,sha256(output.read_bytes()).hexdigest()

if __name__=="__main__":
    import sys
    assert sys.argv[1:] in ([],["--corners"],["--polygon"])
    for meter in (False,True):print(*build(meter,corners=bool(sys.argv[1:]),polygon="--polygon" in sys.argv))
