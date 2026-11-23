"""Read exact float bits of the opaque receiver's direct sunlight before exposure."""
import argparse
from zipfile import ZipFile
from sun_room import source_pack,capture,PACKAGES
from packs import WORK

FINAL="""#version 330 compatibility
#include "/lib/uniforms.glsl"
uniform sampler2D colortex8;
void main() {
    ivec2 xy=ivec2(gl_FragCoord.xy);
    vec3 beam=texelFetch(colortex8,ivec2(xy.x&~3,xy.y),0).rgb;
    if(xy.y==1) beam=sunDirection();
    uvec3 words=floatBitsToUint(beam);
    uvec3 bytes=(words>>uint(8*(xy.x&3)))&255u;
    if(xy.y==2 && xy.x<256) bytes=uvec3(xy.x);
    gl_FragColor=vec4(vec3(bytes)/255.,1.);
}
"""

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",nargs="?",default="baseline",choices=PACKAGES)
    parser.add_argument("--run-label")
    args=parser.parse_args()
    mode=args.mode
    src=source_pack(mode)
    path=WORK/("Aqualumen-Sun-Pane-Meter.zip" if mode=="baseline" else "Aqualumen-Filtered-Sun-Meter.zip")
    if not path.exists():
        with ZipFile(src) as z, ZipFile(path,"x") as m:
            for entry in z.infolist():
                m.writestr(entry,FINAL.encode() if entry.filename=="shaders/final.fsh" else z.read(entry))
    with ZipFile(src) as z, ZipFile(path) as m:
        assert z.namelist()==m.namelist() and m.read("shaders/final.fsh")==FINAL.encode()
        assert all(z.read(n)==m.read(n) for n in z.namelist() if n!="shaders/final.fsh")
    label=args.run_label or ("sun-meter" if mode=="baseline" else "sun-filtered-meter")
    assert label in ("sun-meter","sun-filtered-meter","sun-filtered-meter-r2")
    capture(path,label,180)
