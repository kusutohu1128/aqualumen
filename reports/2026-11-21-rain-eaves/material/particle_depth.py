"""Build an Iris readback for the actual distance, direct light and visibility of a falling particle."""
from copy import copy
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import sys

here = Path(__file__).resolve().parent
root = here.parents[2]
parent = root / "dist/Aqualumen-1.7.0.zip"
output = root / "build/Aqualumen-rain-particle-depth.zip"

def replace(s, key, value):
    assert s.count(key) == 1, key
    return s.replace(key, value)

def modify(name, s):
    if name == "shaders/shaders.properties":
        s += "\nblend.gbuffers_weather.colortex2=off\nblend.gbuffers_weather.colortex3=off\n"
    if name == "shaders/prepare.fsh":
        s = replace(s, "const int colortex0Format", "const int colortex2Format = RGBA16F;\nconst int colortex3Format = RGBA16F;\nconst int colortex0Format")
    if name == "shaders/lib/weather_light.glsl":
        s = replace(s, "vec3 weatherLampLight(", "float nearestDistance=32.0;\nfloat nearestVisibility=0.0;\nvec3 measuredDirect=vec3(0);\nvec3 weatherLampLight(")
        s = replace(s, "        tracedSources++;", "        if(d<nearestDistance){nearestDistance=d;nearestVisibility=dot(vis,vec3(.2126,.7152,.0722));}\n        tracedSources++;")
        s = replace(s, "    return mix(fallback,total", "    measuredDirect=total*coverage;\n    return mix(fallback,total")
    if name == "shaders/gbuffers_weather.fsh":
        s = replace(s, "RENDERTARGETS:0", "RENDERTARGETS:0,2,3")
        s = replace(s, "    gl_FragData[0]", """
    // Matched ordinary fixture lantern cell, at its configured emission offset.
    vec3 q=vec3(406.5,67.44,-434.5)-cameraPosition-position;
    float d=length(q);
    gl_FragData[1]=vec4(d,length(position-relativeWorld(vec3(0))),dot(ray,q/max(d,.0001)),coverage);
    gl_FragData[2]=vec4(measuredDirect,nearestDistance+nearestVisibility*.0);
    gl_FragData[0]""")
    if name == "shaders/final.fsh":
        s = replace(s,"void main()", "void ordinaryFinal()")
        s += """
uniform sampler2D colortex2;
uniform sampler2D colortex3;
void main() {
    ivec2 pixel=ivec2(gl_FragCoord.xy);
    int width=int(viewWidth)/3;
    int panel=pixel.x/width;
    ivec2 q=ivec2(min(3*(pixel.x%width)+1,int(viewWidth)-1),pixel.y);
    vec4 geo=texelFetch(colortex2,q,0);
    vec4 lamp=texelFetch(colortex3,q,0);
    if(panel>=3 || geo.a<.0039) {gl_FragColor=vec4(0,0,0,1);return;}
    vec3 code=panel==0?vec3(geo.x/32.0,geo.y/32.0,geo.z*.5+.5):
              panel==1?sqrt(lamp.rgb/(vec3(1)+lamp.rgb)):vec3(lamp.a/32.0,geo.a,1);
    gl_FragColor=vec4(clamp(code,vec3(0),vec3(1)),1);
}
"""
    return s

if __name__ == "__main__":
    assert hashlib.sha256(parent.read_bytes()).hexdigest()=="eb760f429d32ea03b87d500a5f7d613a1d9a611794e3b2ddb6dd297ec80d4ec8"
    with ZipFile(parent) as z, ZipFile(output,"x") as out:
        for item in z.infolist():
            b=z.read(item)
            if item.filename.startswith("shaders/"):
                b=modify(item.filename,b.decode()).encode()
            out.writestr(copy(item),b)
    pins=here/"packs.json"
    hashes=json.loads(pins.read_text())
    hashes[output.name]=hashlib.sha256(output.read_bytes()).hexdigest()
    pins.write_text(json.dumps(hashes,indent=2)+"\n")
