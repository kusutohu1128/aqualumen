"""Replace only the final display of the QA pack with raw reflection-order samples."""
import argparse
from pathlib import Path
from zipfile import ZipFile
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument("source",type=Path)
ap.add_argument("destination",type=Path)
ap.add_argument("--support-row", action="store_true", help="Display light at wall B and valid ceiling patch coverage")
args=ap.parse_args()
with ZipFile(args.source) as src,ZipFile(args.destination,"x") as dst:
    for entry in src.infolist():
        data=src.read(entry)
        if entry.filename=="shaders/final.fsh":
            data=data.decode().replace("void main() {",'''#include "/lib/bounce_grid.glsl"
uniform sampler2D aqualumenBounceIncident;
uniform sampler2D aqualumenBounceExit;
void main() {
    if(texcoord.y<.3) {
        int i=clamp(int(texcoord.x*3.),0,2);
        vec3 c=i==2?vec3(407,234,-411):vec3(406,234,-412);
        ivec3 cell=ivec3(floor(lampGridPosition(c+vec3(.5)-cameraPosition,cameraPosition)));
        ivec2 patchAddress=2*bounceAddress(cell,2)+ivec2(i==1?1:0);
        int order=int(texcoord.y*10.);
        vec3 linear;
        if(order==0) linear=texelFetch(aqualumenBounceExit,patchAddress,0).rgb;
        else linear=texelFetch(aqualumenBounceIncident,patchAddress+ivec2(0,order==2?1536:0),0).rgb;
        gl_FragColor=vec4(sqrt(clamp(64.*linear,0.,1.)),1.);
        return;
    }
''').encode()
            if args.support_row:
                data=data.replace(b"    if(texcoord.y<.3)",b"""    if(texcoord.y>=.3 && texcoord.y<.5) {
        int i=clamp(int(texcoord.x*3.),0,2);
        if(texcoord.y<.4) {
            vec3 w=vec3(403+i,232,-410);
            ivec3 cell=ivec3(floor(lampGridPosition(w+vec3(.5)-cameraPosition,cameraPosition)));
            vec3 incoming=texelFetch(aqualumenBounceIncident,2*bounceAddress(cell,4),0).rgb;
            gl_FragColor=vec4(sqrt(clamp(16.*incoming,0.,1.)),1.);
        } else {
            vec3 c=i==2?vec3(407,234,-411):vec3(406,234,-412);
            ivec3 cell=ivec3(floor(lampGridPosition(c+vec3(.5)-cameraPosition,cameraPosition)));
            ivec2 addr=2*bounceAddress(cell,2)+ivec2(i==1?1:0);
            float a=texelFetch(aqualumenBounceIncident,addr,0).a;
            float b=texelFetch(aqualumenBounceIncident,addr+ivec2(0,1536),0).a;
            gl_FragColor=vec4(a,b,0,1);
        }
        return;
    }
    if(texcoord.y<.3)""")
        dst.writestr(entry,data)
