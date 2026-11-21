"""Package a private on-screen numerical readout of the real Minecraft shadow capture and lighting."""

import argparse
import subprocess
import tempfile
import zipfile
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[2]

fragment = """#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/local_lighting.glsl"
#include "/lib/bounce_receiver.glsl"
uniform usampler2D aqualumenRawIndex;
const vec2 wall[] = vec2[](vec2(202.5,174.),vec2(201.53,175.5),vec2(203.19,176.05),vec2(200.5,174.2),vec2(204.,173.6),vec2(203.53,177.4));
void main(){
    ivec2 pos=ivec2(gl_FragCoord.xy)/8;
    if(pos.x>=16 || pos.y>=8){gl_FragColor=vec4(0.09,0.12,0.14,1);return;}
    int x=pos.x,y=pos.y;
    vec3 wp=vec3(wall[x%6],366.);
    vec3 rp=wp-cameraPosition;
    ivec3 receiverCell=ivec3(floor(lampGridPosition(rp,cameraPosition)));
    int row=lampLinear(receiverCell/8,8);
    uint value=0u;
    if(y==0){
        ivec3 cell=ivec3(floor(lampGridPosition(vec3(202.5,173.5+float(x%3),364.5)-cameraPosition,cameraPosition)));
        if(x>=3 && x<12) cell=ivec3(floor(lampGridPosition(vec3(201.5+float((x-3)%3),172.5,360.5+float((x-3)/3))-cameraPosition,cameraPosition)));
        value=uint(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
        if(x==12) value=uint(lavaNeighborCount(row));
        if(x==13) value=uint(texelFetch(aqualumenLightList,ivec2(0,row),0).r);
        if(x==14) value=texelFetch(aqualumenRawIndex,ivec2(0,72),0).r;
        if(x==15) value=54321u;
    } else if(x<6){
        vec3 n=vec3(0,0,-1);
        float result;
        if(y<=3) {
            vec3 direct=lampLighting(rp,n,vec3(0),0.,0.,false);
            result=direct[y-1];
        } else if(y==7) result=bounceAtReceiver(rp,n).a;
        else result=bounceAtReceiver(rp,n)[y-4];
        value=uint(round(1e5*clamp(result,0.,160.)));
    }
    gl_FragColor=vec4(vec3(uvec3(value,value>>8u,value>>16u)&255u)/255.,1.);
}
"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pack", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--cells", action="store_true", help="show coordinates of actual nearby fluid cells")
    args = p.parse_args()
    with tempfile.TemporaryDirectory() as work:
        tree = Path(work)
        with zipfile.ZipFile(args.pack) as z:
            assert all(
                n == "LICENSE" or (n.startswith("shaders/") and ".." not in n)
                for n in z.namelist()
            )
            z.extractall(tree)
        shaders = tree / "shaders"
        # Shadow producers, compute passes and consumer functions are byte-identical.
        # The forward beauty shaders are unneeded when the last pass displays data.
        for name in (
            "gbuffers_hand",
            "gbuffers_terrain",
            "gbuffers_textured_lit",
            "gbuffers_water",
            "gbuffers_weather",
        ):
            (shaders / (name + ".fsh")).write_text(
                "#version 430 compatibility\n/* RENDERTARGETS:0 */\nvoid main(){gl_FragData[0]=vec4(.16,.14,.12,1.);}\n"
            )
        cells = """
    ivec2 block=ivec2(gl_FragCoord.xy)/4-ivec2(35,1);
    if(block.x>=0 && block.x<=65 && block.y>=0 && block.y<64){
        ivec3 receiver=ivec3(lampGridPosition(vec3(202.5,174.,366.)-cameraPosition,cameraPosition));
        int row=lampLinear(receiver/8,8);
        int count=lavaNeighborCount(row),k=block.y+1;
        uint value=0u;
        if(block.x==65) value=23456u;
        else if(k<=count){
            int group=int(texelFetch(aqualumenLightField,lavaSourcesAddress(row,k),0).r);
            if(block.x==64) value=uint(group)+1u;
            else{
                ivec3 cell=lampUnpack(group,16)*4+lampUnpack(block.x,4);
                value=uint(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
            }
        }
        gl_FragColor=vec4(vec3(uvec3(value,value>>8u,value>>16u)&255u)/255.,1.);
        return;
    }
"""
        source = fragment.replace("void main(){", "void main(){\n" + cells) if args.cells else fragment
        (shaders / "final.fsh").write_text(source)
        subprocess.run(
            ["python3", here / "build_candidate.py", tree, args.output], check=True
        )


if __name__ == "__main__":
    main()
