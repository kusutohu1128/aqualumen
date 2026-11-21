"""Read the packed halves and shadow-captured sprite data in the private fixture."""
import sys
from zipfile import ZipFile

with ZipFile(sys.argv[1]) as src, ZipFile(sys.argv[2], "x") as out:
    for entry in src.infolist():
        code = src.read(entry)
        if entry.filename == "shaders/final.fsh":
            code = code[:code.index(b"void main()")] + b"""
#include "/lib/local_light_grid.glsl"
uniform sampler2D aqualumenLightField;
uniform usampler2D aqualumenDoorMask;
void main() {
    // Two squares, lower half on the left. Top row encodes cell word bits,
    // the other 16 rows are the published sprite in canonical atlas UV.
    ivec2 p=ivec2(texcoord*vec2(32,17));
    int halfIndex=p.x/16;
    ivec3 world=ivec3(451,151+halfIndex,-422);
    ivec3 cell=ivec3(floor(lampGridPosition(vec3(world)+0.5-cameraPosition,cameraPosition)));
    int word=int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
    int u=p.x%16;
    uint bits=p.y==16?uint(word):texelFetch(aqualumenDoorMask,ivec2(15-p.y,(word>>6)&63),0).r;
    gl_FragColor=vec4(vec3(float((bits>>uint(u))&1u)),1.0);
}
"""
        out.writestr(entry, code)
