"""Derive an isolated observation pack; keep all transport and capture code identical."""
import argparse
from pathlib import Path
from zipfile import ZipFile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("pack", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
if args.output.exists():
    parser.error("choose a new diagnostic ZIP")
with ZipFile(args.pack) as src, ZipFile(args.output, "x") as dst:
    for entry in src.infolist():
        data = src.read(entry)
        if entry.filename == "shaders/lib/terrain.fsh.glsl":
            old = b"gl_FragData[1]=vec4(sunRadiance,1.0);"
            assert data.count(old) == 1
            data = data.replace(old, b"""#ifdef AQUALUMEN_TERRAIN_BOUNCE
    gl_FragData[1]=vec4(bounceAtReceiver(worldPosition,normal).rgb,1.0);
#else
    gl_FragData[1]=vec4(0);
#endif""")
        if entry.filename == "shaders/final.fsh":
            data = b"""#version 330 compatibility
uniform sampler2D colortex5;
void main() {
    vec3 reflected=texelFetch(colortex5,ivec2(gl_FragCoord.xy),0).rgb;
    gl_FragColor=vec4(sqrt(clamp(reflected*4.0,0.0,1.0)),1.0);
}
"""
        dst.writestr(entry, data)
