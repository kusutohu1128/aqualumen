// Screen-space horizon estimate for the diffuse sky near terrain contacts.
// A plane leaves the hemisphere open. Missing and distant samples contribute
// no occluder. Pixel centres and eight fixed azimuths avoid temporal dithering.
float contactSkyVisibility(vec2 uv,vec3 view,vec3 normal,sampler2D depthMap) {
    const float radius=1.25;
    float eyeDepth=-view.z;
    if(eyeDepth<0.05 || eyeDepth>48.0) return 1.0;
    vec2 projected=vec2(gbufferProjection[0][0],gbufferProjection[1][1])*0.5*radius/eyeDepth;
    ivec2 size=textureSize(depthMap,0);
    float blocked=0.0;
    for(int i=0;i<8;++i) {
        float angle=(float(i)+0.5)*PI/4.0;
        vec2 delta=vec2(cos(angle),sin(angle))*projected;
        float horizon=0.0;
        for(int j=1;j<=3;++j) {
            float fraction=float(j)/3.0;
            vec2 probe=uv+delta*fraction*fraction;
            if(any(lessThan(probe,vec2(0))) || any(greaterThanEqual(probe,vec2(1)))) continue;
            ivec2 pixel=ivec2(probe*vec2(size));
            float d=texelFetch(depthMap,pixel,0).r;
            if(d>=0.999999) continue;
            vec3 offset=viewPosition((vec2(pixel)+0.5)/vec2(size),d)-view;
            float dist=length(offset);
            float sine=max(dot(offset,normal)-0.025,0.0)/max(dist,0.025);
            // Lambert-weighted blocked fraction from tangent to the horizon.
            horizon=max(horizon,sine*sine*(1.0-smoothstep(0.15,radius,dist)));
        }
        blocked+=horizon;
    }
    return 1.0-blocked/8.0*(1.0-smoothstep(32.0,48.0,eyeDepth));
}
