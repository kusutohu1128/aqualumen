#include "/lib/local_light_grid.glsl"
#include "/lib/open_cell_layout.glsl"
uniform sampler2D aqualumenLightField;
uniform sampler2D aqualumenLightList;

int forestSample(ivec2 pixel) {
    ivec3 cell=lampUnpack((pixel.x%512)+512*pixel.y,64);
    if(pixel.x<512) return int(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
    if(pixel.x>=1024) return 0;
    const ivec3 locations[4]=ivec3[4](ivec3(207,64,359),ivec3(210,64,359),ivec3(205,64,357),ivec3(208,64,360));
    int flags=int(texelFetch(aqualumenLightField,openCellAddress(cell),0).r);
    int row=lampLinear(cell/8,8);
    int count=min(lampCapacity,int(texelFetch(aqualumenLightList,ivec2(0,row),0).r));
    int state=0;
    for(int k=0;k<count;k++) {
        vec4 light=texelFetch(aqualumenLightList,ivec2(k+1,row),0);
        if((int(light.w)&lampCarriedFlag)!=0) continue;
        ivec3 world=ivec3(floor(light.xyz))+8*openTileOrigin();
        for(int j=0;j<4;j++) if(all(equal(world,locations[j]))) {
            int route=(flags&(1<<k))!=0?2:(flags&(1<<(12+k)))!=0?3:1;
            state|=route<<(2*j);
        }
    }
    return state;
}

void main() {
    ivec2 pixel=ivec2(gl_FragCoord.xy);
    int value=pixel.y<512?forestSample(pixel):0;
    if(pixel.y==513 && pixel.x<256) value=pixel.x*65793;
    if(pixel.y==514 && pixel.x<3) value=8*openTileOrigin()[pixel.x]+32768;
    gl_FragColor=vec4(vec3(value&255,(value>>8)&255,(value>>16)&255)/255.,1.);
}
