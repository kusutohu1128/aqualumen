// Lower-hemisphere irradiance on a submerged vertical bank. Each of two
// cosine-weighted directions samples a real sunlit horizontal bed. Its solid
// angle weight is half the Lambert hemisphere, split between the two rays.
vec3 bedBounce(vec3 point, vec3 normal, vec3 albedo, float surfaceY, vec3 sun) {
    if(abs(normal.y)>0.1 || surfaceY<=point.y) return vec3(0.0);
    vec3 tangent=vec3(-normal.z,0.0,normal.x);
    vec3 indirect=vec3(0.0);
    for(int i=0;i<2;++i) {
        vec3 ray=normalize(normal*0.72+vec3(0.0,-0.62,0.0)+tangent*(i==0?-0.42:0.42));
        WaterBed floorHit;
        if(lightViewBed(point+0.025*normal,ray,6.0,floorHit) && floorHit.normal.y>0.99) {
            vec3 sunLight=SOLAR*localSolarTransmission(floorHit.point,sun,colortex6)*max(sun.y,0.0)
                *shadowVisibility(floorHit.point,floorHit.normal)*smoothstep(0.0,0.85,floorHit.lightmap.y)
                *(1.0-0.85*rainStrength);
            float depth=max(surfaceY-floorHit.point.y,0.0);
            float skyAccess=smoothstep(0.0,1.0,floorHit.lightmap.y)*floorHit.material.a;
            vec3 incoming=sunLight/PI*waterSunBeamTransmission(depth,sun)
                +skyAccess*submergedDiffuseFace(floorHit.normal,depth);
            vec3 floorAlbedo=immersedAlbedo(pow(floorHit.material.rgb,vec3(2.2)),floorHit.granular);
            indirect+=0.25*floorAlbedo*incoming*waterTransmission(floorHit.travel);
        }
    }
    return albedo*indirect;
}
vec3 lookupBedBounce(vec2 screen,vec3 point,float surfaceY,vec3 sun) {
    vec4 material=texelFetch(colortex10,ivec2(screen*vec2(textureSize(colortex10,0))),0);
    int tag=bedFaceCode(material);
    if(tag<2 || tag>7) return vec3(0.0);
    return bedBounce(point,bedNormal(tag),immersedAlbedo(pow(material.rgb,vec3(2.2)),isGranular(material)),surfaceY,sun);
}
