"""Capture actual biased ray origins, source directions and horizontal pixel neighbours."""
from pack import HERE, WORK, build, replace
from swept import METER,changed
NAME=METER.replace("-Meter","-Coordinates")
def instrument(name,s):
    return add_coordinates(name,changed(name,s,True))

def add_coordinates(name,s):
    if name=="shaders/lib/local_lighting.glsl":
        s=replace(s,"vec3 probePosition=vec3(0.);","vec3 probePosition=vec3(0.),probeOffset=vec3(0.);")
        s=replace(s,"            probeNormal=0;","            probeOffset=origin-p;\n            probeNormal=0;")
    if name=="shaders/prepare.fsh":
        s=replace(s,"const int colortex2Format","const int colortex3Format = RGBA32F;\nconst int colortex2Format")
    if name=="shaders/deferred.fsh":
        s=replace(s,"RENDERTARGETS:0,4,8,10,14,1,2","RENDERTARGETS:0,4,8,10,14,1,2,3")
        s=replace(s,"gl_FragData[6]=vec4(probePosition.xy,probePosition.z+128.*float(axisFace),1.);",
                  "gl_FragData[6]=vec4(probePosition,1.);gl_FragData[7]=vec4(probeOffset,1.);")
    if name=="shaders/final.fsh":
        s=replace(s,"uniform sampler2D colortex1;","uniform sampler2D colortex3;\nuniform sampler2D colortex1;")
        a=s.index("    ivec2 meterPixel=");b=s.index("    gl_FragColor=vec4(rgb,1.);",a)
        s=s[:a]+"""    ivec2 pixelHere=ivec2(gl_FragCoord.xy),at=ivec2(pixelHere.x,pixelHere.y&~15);
    int lane=pixelHere.y&15;
    vec4 lamps=texelFetch(colortex1,at,0),position=texelFetch(colortex2,at,0);
    vec3 offset=texelFetch(colortex3,at,0).rgb;
    vec3 rgb=vec3(0);
    if(lane<4) rgb=probeBytes(int(lamps[lane]));
    else if(lane<7) rgb=probeBytes(int(round(clamp(position[lane-4],0.,127.)*65536.)));
    else if(lane<10) rgb=probeBytes(int(round((offset[lane-7]+1.)*1048576.)));
    else if(lane==10) rgb=vec3(51.,183.,cameraPosition.x>300.?1.:2.)/255.;
    if(pixelHere.y==2 && pixelHere.x<256) rgb=vec3(float(pixelHere.x)/255.);
"""+s[b:]
    return s
if __name__=="__main__": print(NAME,build(WORK/NAME,instrument))
