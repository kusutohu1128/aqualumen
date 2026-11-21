"""Build a TEST-only raw view of land shadow path, visibility and sun incidence."""
import argparse
from pathlib import Path
from zipfile import ZipFile


def build(source, output, metric):
    with ZipFile(source) as pack:
        entries = [(info, pack.read(info)) for info in pack.infolist()]
    changes = {}
    for info, content in entries:
        if info.filename == "shaders/lib/terrain.fsh.glsl":
            marker = b"gl_FragData[1]=vec4(sunRadiance,1.0);"
            if content.count(marker) != 1:
                raise ValueError("Unexpected terrain output")
            sample = ("LandShadowReceiver probe=makeLandShadowReceiver(worldPosition,normal);\n"
                      "float path=probe.outcome==LAND_SHADOW_METRIC?1.0:(probe.outcome==LAND_SHADOW_LEGACY?0.5:0.25);\n"
                      "float vis=landShadowVisibility(worldPosition,normal);" if metric else
                      "float path=0.5;\nfloat vis=shadowVisibility(worldPosition,normal);")
            changes[info.filename] = content.replace(marker,(sample+
                "\ngl_FragData[1]=vec4(path,vis,max(dot(normal,sunDirection()),0.0),1.0);").encode())
        if info.filename == "shaders/final.fsh":
            changes[info.filename] = b"""#version 330 compatibility
#include "/lib/uniforms.glsl"
uniform sampler2D colortex5;
float header(int i) {
    if (i < 16) return gbufferProjectionInverse[i / 4][i % 4];
    if (i < 32) return gbufferModelViewInverse[(i-16) / 4][(i-16) % 4];
    if (i < 35) return cameraPosition[i-32];
    if (i < 38) return sunDirection()[i-35];
    if (i < 41) return shadowDirection()[i-38];
    if (i < 57) return shadowModelView[(i-41) / 4][(i-41) % 4];
    if (i < 73) return shadowProjection[(i-57) / 4][(i-57) % 4];
    return 123.5;
}
void main() {
    ivec2 p = ivec2(gl_FragCoord.xy);
    int idx = p.y == 0 ? p.x : p.y == 490 ? p.x - 780 : -1;
    if (idx >= 0 && idx < 148) {
        uint u = floatBitsToUint(header(idx / 2)) >> uint((idx % 2) * 16);
        gl_FragColor = vec4(float(u & 255u)/255.0,float((u >> 8u) & 255u)/255.0,1.0,1.0);
    } else gl_FragColor=vec4(texelFetch(colortex5,p,0).rgb,1.0);
}
"""
    if len(changes) != 2:
        raise ValueError("Missing diagnostic outputs")
    with ZipFile(output, "x") as target:
        for info, content in entries:
            target.writestr(info,changes.get(info.filename,content))


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path)
    p.add_argument("output",type=Path)
    p.add_argument("--metric",action="store_true")
    a=p.parse_args()
    build(a.source,a.output,a.metric)
