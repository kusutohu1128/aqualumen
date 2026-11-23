"""Build private open-path trials on the byte-identified wet-plane pack."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / "build/torch-open-volume"
BASE = ROOT / "dist/Aqualumen-Wet-Plane-Study.zip"
BASE_SHA = "8df2a8fcd645d58f0423d8b9974f99a186022d345c44a2ef9404b05a9c6a52c2"


def insert(source, marker, value):
    assert source.count(marker) == 1, marker
    return source.replace(marker, value)


def build(meter=False,work=WORK,base_path=BASE):
    assert sha256(base_path.read_bytes()).hexdigest() == BASE_SHA
    work.mkdir(parents=True,exist_ok=True)
    path = work / ("Aqualumen-Open-Volume-Meter.zip" if meter else "Aqualumen-Open-Volume.zip")
    with ZipFile(base_path) as base, ZipFile(path, "w") as out:
        for entry in base.infolist():
            name = entry.filename
            data = base.read(entry)
            if name == "shaders/shaders.properties":
                data = insert(data,b"float false false 512 2112\n",b"float false false 512 2624\n")
            elif name == "shaders/lib/local_lighting.glsl":
                source = data.decode()
                point = "// Fixed quadrature"
                source = insert(source,point,"#ifdef OPEN_TERRAIN_PATH\n"+(HERE/"open.glsl").read_text()+"#endif\n"+point)
                point = "    vec3 axis=abs(l.y)<0.9?"
                source = insert(source,point,"""#ifdef OPEN_TERRAIN_PATH
    if(!carried && !occluders.leafVolume && !occluders.entityTest && openLampPath(start,centre,radius)) {
#ifndef OPEN_PATH_METER
        return vec3(1);
#else
        auditOpen=true;
#endif
    }
#endif
"""+point)
                if meter:
                    point = "bool openLampPath("
                    source = insert(source,point,"bool auditOpen=false;\nint traceCalls=0,openCalls=0,badCalls=0,bodyCalls=0;\nfloat visibilitySum=0.;\n"+point)
                    point = "        vec3 vis=lampVisibility(origin,lamp.xyz,l,radius,carried,occluders);"
                    source = insert(source,point,"#ifdef OPEN_TERRAIN_PATH\n        auditOpen=false;\n#endif\n"+point+"""
#ifdef OPEN_TERRAIN_PATH
        if(!carried) {
            traceCalls++;
            visibilitySum+=vis.g;
            if(occluders.entityTest) bodyCalls++;
        }
        if(auditOpen) {
            openCalls++;
            if(any(notEqual(vis,vec3(1)))) badCalls++;
        }
#endif""")
                data = source.encode()
            elif name == "shaders/deferred.fsh":
                source = data.decode()
                marker = '#include "/lib/local_lighting.glsl"'
                defs = "#define OPEN_TERRAIN_PATH\n" + ("#define OPEN_PATH_METER\n" if meter else "")
                source = insert(source,marker,defs+marker)
                if meter:
                    source = insert(source,"RENDERTARGETS:0,4,8,10,14","RENDERTARGETS:0,4,8,10,14,2")
                    point = "    gl_FragData[3]=material;"
                    source = insert(source,point,point+"""
    int surface=0;
    if(depth<.999999 && directSun.a<-.5) {
        vec3 w=relativeWorld(viewPosition(texcoord,depth))+cameraPosition;
        if(w.x>404. && w.x<410. && w.z> -412. && w.z< -405. && abs(w.y-151.)<.006) surface=1;
        if(w.x>404. && w.x<410. && w.y>151. && w.y<155. && abs(w.z+412.)<.006) surface=2;
    }
    gl_FragData[5]=vec4(float(surface*16+traceCalls),float(openCalls),
                        float(16*bodyCalls+badCalls),visibilitySum);""")
                data = source.encode()
            elif meter and name == "shaders/prepare.fsh":
                point = b"const int colortex0Format"
                data = insert(data,point,b"const int colortex2Format = RGBA16F;\n"+point)
            elif meter and name == "shaders/final.fsh":
                data = insert(data,b"void main() {",b"""uniform sampler2D colortex2;
void main() {
    ivec2 auditPixel=ivec2(gl_FragCoord.xy);
    if(auditPixel.y==2 && auditPixel.x<256) gl_FragColor=vec4(vec3(auditPixel.x)/255.,1.);
    else {
        vec4 values=texelFetch(colortex2,ivec2(auditPixel.x & ~1,auditPixel.y),0);
        float rays=mod(values.r,16.);
        gl_FragColor=vec4((auditPixel.x&1)==0?values.rgb/255.:vec3(values.a/max(1.,rays)),1.);
    }
    return;
""")
            out.writestr(entry,data)
        include = "shaders/lib/open_volume_integrate.glsl"
        additions = {include:(HERE/"integrate.glsl").read_text()}
        for axis in range(3):
            additions[f"shaders/shadowcomp{axis+5}.csh"] = f'#version 430 compatibility\n#define OPEN_AXIS {axis}\n#include "/lib/open_volume_integrate.glsl"\n'
        for name, source in additions.items():
            assert name not in base.namelist()
            entry = ZipInfo(name,(2026,10,1,0,0,0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            out.writestr(entry,source)
    return path


if __name__ == "__main__":
    for meter in (False,True):
        pack = build(meter)
        print(sha256(pack.read_bytes()).hexdigest(),pack)
