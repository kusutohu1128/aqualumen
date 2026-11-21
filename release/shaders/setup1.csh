#version 430 compatibility
layout(local_size_x=1) in;
const ivec3 workGroups = ivec3(1,1,1);
layout(rg32f) uniform writeonly image2D lampExposureImage;
void main() {
    imageStore(lampExposureImage,ivec2(0),vec4(1.0,1729.0,0,0));
}
