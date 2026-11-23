#include "/lib/canopy_grid.glsl"
#include "/lib/canopy_distant.glsl"
uniform sampler2D aqualumenLampExposure;

// Blend the received *radiance* of the axis faces before turning it back
// into an access ratio. On a rotating leg a bright blue opening and a dark
// warm horizon generally carry different energy at the same normal weight.
vec3 animalSky(vec3 relative,vec3 n) {
    if(aqualumenDimension!=0 || textureSize(aqualumenLampExposure,0)!=ivec2(198,1090))
        return vec3(1);
    float range=canopyRange(relative);
    vec3 distant=range<1.?canopyDistantAccess(relative,n):vec3(1);
    if(range<=0.) return distant;
    vec3 p=lampGridPosition(relative,cameraPosition)-vec3(canopyOrigin());
    ivec3 base=ivec3(floor(p));
    vec3 f=fract(p),open=vec3(0),incident=vec3(0);
    for(int axis=0;axis<3;axis++) {
        if(abs(n[axis])<.0001) continue;
        int face=2*axis+int(n[axis]>0.);
        vec3 value=n[axis]*n[axis]*texelFetch(colortex11,ivec2(face,0),0).rgb;
        vec3 access=vec3(1);
        if(face!=2) {
            access=vec3(0);
            for(int i=0;i<8;i++) {
                ivec3 offset=ivec3(i&1,(i>>1)&1,i>>2);
                vec3 w=mix(1.-f,f,vec3(offset));
                access+=w.x*w.y*w.z*canopyUnpack(texelFetch(aqualumenLampExposure,canopyAddress(base+offset,face),0).rg);
            }
        }
        open+=value;
        incident+=value*access;
    }
    return mix(distant,(incident+1e-7)/(open+1e-7),range);
}
