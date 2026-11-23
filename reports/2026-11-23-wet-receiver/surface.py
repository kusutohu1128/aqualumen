"""Read the stored normal code and branch on the same fragments as the HDR comparison."""
from paired import HERE, WORK, build, diagnostic, render, replace

SURVEY=WORK/"Aqualumen-Surface-Readout.zip"


def normal_fields(name,shader):
    shader=diagnostic(name,shader)
    if name!="shaders/final.fsh":
        return shader
    shader=replace(shader,"uniform sampler2D colortex2;",'#include "/lib/area_receiver.glsl"\nuniform sampler2D colortex15;\nuniform sampler2D colortex2;')
    shader=replace(shader,"    if(all(equal(panel,ivec2(1,1)))) return false;\n","")
    return replace(shader,"    float err=panel.x==0?v.r:v.g;", """    if(all(equal(panel,ivec2(1,1)))) {
        vec4 s=texelFetch(colortex15,ivec2(sampleTop.x,size.y-1-sampleTop.y),0);
        float tag=s.z<0.?7.:(s.w<0.?-s.w:0.);
        vec3 n=s.z<0.?vec3(0.,1.,0.):areaDecodeNormal(s.w);
        vec2 tilt=clamp(round(16384.*n.xz)+128.,0.,255.);
        gl_FragColor=vec4(vec3(tag,tilt)/255.,1.);
        return true;
    }
    float err=panel.x==0?v.r:v.g;""")


if __name__=="__main__":
    digest=build(SURVEY,normal_fields)
    print(digest,flush=True)
    render(SURVEY,digest,"surface")
