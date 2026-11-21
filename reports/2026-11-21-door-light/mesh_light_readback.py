"""Encode the actual terrain mesh lightmap and vertex AO in a private diagnostic pack."""
from pathlib import Path
import sys
from zipfile import ZipFile


def write(source, target):
    with ZipFile(source) as src, ZipFile(target, "x") as out:
        for entry in src.infolist():
            code = src.read(entry)
            if entry.filename == "shaders/lib/terrain.fsh.glsl":
                pos = code.rindex(b"}")
                code = code[:pos] + b"    gl_FragData[2]=vec4(lightmap,vertexColor.a,dot(localRadiance,vec3(0.2126,0.7152,0.0722)));\n" + code[pos:]
            elif entry.filename == "shaders/final.fsh":
                pos = code.index(b"void main()")
                code = code[:pos] + b"""
uniform sampler2D colortex9;
uniform sampler2D colortex4;
uniform sampler2D colortex8;
void main() {
    ivec2 p=ivec2(gl_FragCoord.xy);
    vec4 mesh=texelFetch(colortex9,p,0);
    vec3 luma=vec3(0.2126,0.7152,0.0722);
    float sun=dot(texelFetch(colortex8,p,0).rgb,luma);
    float total=dot(texelFetch(colortex4,p,0).rgb,luma);
    // Alternate raw mesh rows with sqrt-encoded scene-linear radiance.
    vec3 energy=vec3(mesh.a,sun,total-sun-mesh.a);
    gl_FragColor=vec4((p.y&1)==0?mesh.rgb:sqrt(max(energy,vec3(0.0))),1.0);
}
"""
            out.writestr(entry, code)


if __name__ == "__main__":
    write(Path(sys.argv[1]), Path(sys.argv[2]))
