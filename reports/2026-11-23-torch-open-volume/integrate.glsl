// Each lane owns an entire disjoint line. Iris inserts the image and texture
// barriers between the three shadowcomp dispatches and the terrain draw.
#include "/lib/local_light_grid.glsl"
layout(local_size_x=8,local_size_y=8) in;
const ivec3 workGroups=ivec3(8,8,1);
layout(r32f) uniform image2D lampFieldImage;
void main() {
    ivec2 p=ivec2(gl_GlobalInvocationID.xy);
    int count=0;
    for(int k=0;k<64;k++) {
#if OPEN_AXIS == 0
        ivec3 cell=ivec3(p.x,k,p.y);
#elif OPEN_AXIS == 1
        ivec3 cell=ivec3(p.x,p.y,k);
#else
        ivec3 cell=ivec3(k,p.y,p.x);
#endif
        ivec2 source=lampCellAddress(cell);
        ivec2 address=source+ivec2(0,2112);
#if OPEN_AXIS == 0
        count+=int((int(imageLoad(lampFieldImage,source).r)&63)!=0);
#else
        count+=int(imageLoad(lampFieldImage,address).r);
#endif
        imageStore(lampFieldImage,address,vec4(float(count)));
    }
}
