#include "/lib/canopy_grid.glsl"
#include "/lib/canopy_distant.glsl"
uniform sampler2D aqualumenLampExposure;

vec3 canopyAtVertex(vec3 relative,vec3 normal) {
    float range=canopyRange(relative);
    if(aqualumenDimension!=0 || textureSize(aqualumenLampExposure,0)!=ivec2(198,1090))
        return vec3(1);
    vec3 distant=range<1.?canopyDistantAccess(relative,normal):vec3(1);
    if(range<=0.) return distant;
    vec3 p=lampGridPosition(relative,cameraPosition)-vec3(canopyOrigin());
    // Full cube faces share exact lattice vertices across neighbouring quads.
    // Snap roundoff in camera-relative coordinates before interpolating plants.
    vec3 rounded=round(p);
    p=mix(p,rounded,lessThan(abs(p-rounded),vec3(.002)));
    ivec3 base=ivec3(floor(p));
    vec3 f=fract(p),access=vec3(0);
    for(int axis=0;axis<3;axis++) {
        float weight=normal[axis]*normal[axis];
        if(weight<.0001) continue;
        int face=2*axis+int(normal[axis]>0.);
        if(face==2) {access+=weight;continue;}
        for(int j=0;j<8;j++) {
            ivec3 stepCell=ivec3(j&1,(j>>1)&1,j>>2);
            vec3 w=mix(1.-f,f,vec3(stepCell));
            float share=w.x*w.y*w.z;
            if(share>0.) access+=weight*share*canopyUnpack(texelFetch(aqualumenLampExposure,canopyAddress(base+stepCell,face),0).rg);
        }
    }
    return mix(distant,access,range);
}
