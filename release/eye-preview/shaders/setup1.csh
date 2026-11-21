#version 430 compatibility
layout(local_size_x=1) in;
const ivec3 workGroups = ivec3(1,1,1);
layout(rg32f) uniform writeonly image2D lampExposureImage;
void main() {
    imageStore(lampExposureImage,ivec2(0),vec4(1.0,1729.0,0,0));
    // The first metered frame supplies the daylight gain on world load.
    if(imageSize(lampExposureImage).x>1)
        imageStore(lampExposureImage,ivec2(1,0),vec4(0));
}
