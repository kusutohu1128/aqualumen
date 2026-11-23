"""Create the matched normal and meter packs for the finite-source terrain scan."""
from hashlib import sha256
import math
import sys
from zipfile import ZipFile

from motion import HERE, PACKS, WORK


def shader(text, meter, multiple=False):
    marker="float continuousBox("
    assert text.count(marker)==1
    model=(HERE/("cone_many.glsl" if multiple else "cone.glsl")).read_text()
    if multiple:
        taps=[]
        for i in range(64):
            r=math.sqrt((i+.5)/64)
            angle=i*2.399963229728653+.417
            taps.append(f"vec2({r*math.cos(angle):.9f},{r*math.sin(angle):.9f})")
        model="const vec2 terrainConeDisk[64]=vec2[64](\n    "+",\n    ".join(taps)+");\n\n"+model
    text=text.replace(marker,model+"\n"+marker)
    text=text.replace("out vec3 lo,out vec3 hi,out vec3 loB,out vec3 hiB,out bool pair,out vec2 witness)",
                      "out vec3 lo,out vec3 hi,out vec3 loB,out vec3 hiB,out bool pair,out vec2 witness,bool exact)")
    mark="continuousBox(cell,slot,start,centre,u,v,radius,lo,hi,loB,hiB,pair,witness)"
    assert text.count(mark)==1 and text.count("witness,bool exact)")==1
    text=text.replace(mark,mark[:-1]+",!occluders.entityTest)")
    mark="if(area<=0. || area>=1.) return area;"
    assert text.count(mark)==1
    text=text.replace(mark,"if(exact || area<=0. || area>=1.) return area;")
    mark="                // A fully visible static disk still needs the usual animal shadow.\n            }\n        }"
    assert text.count(mark)==1
    marker="                probeMethod=0;\n" if meter else ""
    text=text.replace(mark,mark+"""
        if(!occluders.entityTest && all(greaterThan(min(fract(start),1.-fract(start)),vec3(.0001)))) {
            float area=terrainConeVisibility(start,centre,u,v);
            if(area>=0.) {
"""+marker+"""                return vec3(area);
            }
        }""")
    return text


def with_entities(text):
    def replace_once(source, before, after):
        assert source.count(before)==1
        return source.replace(before,after)

    # Static geometry must have the same area even when a moving entity
    # enters the broad test without actually intersecting any lamp ray.
    text=replace_once(text,"out vec2 witness,bool exact)","out vec2 witness)")
    text=replace_once(text,"loB,hiB,pair,witness,!occluders.entityTest)","loB,hiB,pair,witness)")
    start=text.index("    if(exact || area<=0.")
    end=text.index("\n}",start)
    text=text[:start]+"    return area;"+text[end:]
    text=text[:text.index("float planeBoxDistance2(")]+text[text.index("void readBox("):]
    text=text[:text.index("bool crossesPair(")]+text[text.index("const vec2 terrainConeDisk[64]"):]
    text=replace_once(text,"vec3 openSurfaceNormal;\n","")
    text=replace_once(text,"openSurfaceNormal=normal;","")
    text=replace_once(text,"float terrainConeVisibility(vec3 start,vec3 source,vec3 u,vec3 v)",
                      "float terrainConeVisibility(vec3 start,vec3 source,vec3 u,vec3 v,inout LampOccluders o)")
    text=replace_once(text,"if(!occluders.entityTest && all(greaterThan(min(fract(start)",
                      "if(all(greaterThan(min(fract(start)")
    text=replace_once(text,"terrainConeVisibility(start,centre,u,v)","terrainConeVisibility(start,centre,u,v,occluders)")
    start=text.index("    if(count==0) return 1.;",text.index("float terrainConeVisibility("))
    end=text.index("    // Three or more",start)
    text=text[:start]+"""    // A fully visible disk can use the ordinary entity sampler.
    if(count==0) return o.entityTest?-1.:1.;
    if(count<=2) {
        vec2 witness;
        vec3 second=count==2?boxes[1]:vec3(0.);
        float area=count==2?twoBlockers(boxes[0],boxes[0]+1.,second,second+1.,delta,u,v,extent,witness)
                           :oneBlocker(boxes[0],boxes[0]+1.,delta,u,v,extent,witness);
        if(!o.entityTest || area<=0.) return area;
        if(area>=1.) return -1.;
        return jointDiskSamples(start,source,u,v,boxes[0],boxes[0]+1.,area,witness,false,count==2,second,second+1.,o).r;
    }
"""+text[end:]
    text=replace_once(text,"    int visible=0;\n    for(int j=0;j<64;j++)",
                      "    int visible=0,bodyRays=0;\n    float pastBody=0.;\n    for(int j=0;j<64;j++)")
    text=replace_once(text,"vec2 tap=terrainConeDisk[j];","vec2 tap=terrainConeDisk[(17*j)&63];")
    text=replace_once(text,"        if(!blocked) visible++;","""        if(blocked) continue;
        visible++;
#if ENTITY_LIGHT_SHADOWS == 1
        // Average the current body transmission only on open terrain rays.
        // Keep counting static visibility after the triangle budget runs out.
        if(o.entityTest && bodyRays<24 && o.work>0) {
            float trans=entityTransmission(o.entities,start+o.toRelative,start+ray+o.toRelative,false,o.work);
            if(o.work>0 || bodyRays==0) {pastBody+=trans;bodyRays++;}
        }
#endif""")
    return replace_once(text,"    return float(visible)/64.;",
                        "    float body=bodyRays>0?pastBody/float(bodyRays):1.;\n    return float(visible)/64.*body;")


if __name__=="__main__":
    assert sys.argv[1:] in ([],["--multiple"],["--entities"])
    multiple=bool(sys.argv[1:])
    entities=sys.argv[1:]==["--entities"]
    for name,digest in PACKS:
        src=WORK/name
        variant="joint-cone" if entities else "cone64" if multiple else "cone"
        dest=WORK/name.replace("caps",variant)
        assert sha256(src.read_bytes()).hexdigest()==digest
        with ZipFile(src) as original,ZipFile(dest,"w") as archive:
            for entry in original.infolist():
                data=original.read(entry)
                if entry.filename=="shaders/lib/local_lighting.glsl":
                    text=shader(data.decode(),"meter" in name,multiple)
                    data=(with_entities(text) if entities else text).encode()
                archive.writestr(entry,data)
        print(dest.name,sha256(dest.read_bytes()).hexdigest())
