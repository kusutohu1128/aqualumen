"""Capture both placed-torch visibility estimates on identical Minecraft fragments."""
from pack import HERE, NAME, WORK, build, replace

METER_NAME=NAME.replace("-Study","-Meter2")
GLOBALS="""
bool probeBaseline=false;
int probeMethod=0;
vec4 probeLamps=vec4(0.);
vec3 probePosition=vec3(0.);
int probeNormal=0;
int probeScene() { return cameraPosition.x>300.?1:2; }
int probeLight(vec3 grid) {
    vec3 world=grid+8.*floor(cameraPosition/8.)-32.;
    ivec3 block=ivec3(floor(world));
    if(probeScene()==1) return all(equal(block,ivec3(405,151,-408)))?0:-1;
    if(all(equal(block,ivec3(207,64,359)))) return 0;
    if(all(equal(block,ivec3(210,64,359)))) return 1;
    if(all(equal(block,ivec3(205,64,357)))) return 2;
    if(all(equal(block,ivec3(208,64,360)))) return 3;
    return -1;
}
"""
PROBE="""
#ifdef OPEN_TERRAIN_PATH
        LampOccluders baselineOccluders=occluders;
        probeBaseline=true;
        vec3 oldVis=lampVisibility(origin,lamp.xyz,l,radius,carried,baselineOccluders);
        probeBaseline=false;
        probeMethod=0;
#endif
        vec3 vis=lampVisibility(origin,lamp.xyz,l,radius,carried,occluders);
#ifdef OPEN_TERRAIN_PATH
        int id=probeLight(lamp.xyz);
        if(!carried && id>=0) {
            int flags=64+probeMethod+(behind?4:0)+(occluders.entityTest?8:0);
            probeLamps[id]=float(int(round(oldVis.g*255.))+256*int(round(vis.g*255.))+65536*flags);
            probePosition=p+8.*floor(cameraPosition/8.)-32.-(probeScene()==1?vec3(384,128,-432):vec3(176,32,320));
            probeNormal=0;
            for(int a=0;a<3;a++) if(abs(normal[a])>.99999) probeNormal=1+2*a+(normal[a]>0.?1:0);
        }
#endif"""
FINAL="""
uniform sampler2D colortex1;
uniform sampler2D colortex2;
vec3 probeBytes(int v) { return vec3(v&255,(v>>8)&255,(v>>16)&255)/255.; }
void main() {
    ivec2 meterPixel=ivec2(gl_FragCoord.xy),at=ivec2(meterPixel.x&~7,meterPixel.y);
    int lane=meterPixel.x&7;
    vec4 lamps=texelFetch(colortex1,at,0),position=texelFetch(colortex2,at,0);
    vec3 rgb;
    if(lane<4) rgb=probeBytes(int(lamps[lane]));
    else if(lane<7) rgb=probeBytes(int(round(clamp(position[lane-4],0.,127.)*65536.)));
    else rgb=vec3(position.w,183.,cameraPosition.x>300.?1.:2.)/255.;
    if(meterPixel.y==2 && meterPixel.x<256) rgb=vec3(float(meterPixel.x)/255.);
    gl_FragColor=vec4(rgb,1.);
    return;
"""

def audit(name,s):
    if name=="shaders/lib/local_lighting.glsl":
        key="int openReceiverRow,openSourceSlot;"
        s=replace(s,key,key+GLOBALS)
        s=replace(s,"if((flags&(1<<openSourceSlot))!=0) return vec3(1);",
                    "if((flags&(1<<openSourceSlot))!=0) { probeMethod=1; return vec3(1); }")
        s=replace(s,"if((flags&(1<<(openSourceSlot+12)))!=0)\n            return vec3(cachedBoxVisibility(cell,start,centre,u,v,radius));",
                    "if(!probeBaseline && (flags&(1<<(openSourceSlot+12)))!=0) { probeMethod=2; return vec3(cachedBoxVisibility(cell,start,centre,u,v,radius)); }")
        s=replace(s,"        vec3 vis=lampVisibility(origin,lamp.xyz,l,radius,carried,occluders);",PROBE)
    if name=="shaders/deferred.fsh":
        s=replace(s,"RENDERTARGETS:0,4,8,10,14","RENDERTARGETS:0,4,8,10,14,1,2")
        s=replace(s,"    gl_FragData[3]=material;","    gl_FragData[3]=material;\n    gl_FragData[5]=probeLamps; gl_FragData[6]=vec4(probePosition,float(probeNormal));")
    if name=="shaders/prepare.fsh":
        s=replace(s,"const int colortex0Format","const int colortex1Format = RGBA32F;\nconst int colortex2Format = RGBA32F;\nconst int colortex0Format")
    if name=="shaders/final.fsh":
        s=replace(s,"void main() {",FINAL)
    return s

if __name__=="__main__":
    print(build(WORK/METER_NAME,audit))
