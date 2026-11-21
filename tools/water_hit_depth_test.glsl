struct WaterPrimaryHit {
    bool accepted;
    vec3 point;
    vec3 viewPoint;
    float windowDepth;
};
WaterPrimaryHit waterPrimaryHit(vec3 rasterPoint,vec3 solvedPoint,int solveStatus) {
    WaterPrimaryHit hit=WaterPrimaryHit(false,rasterPoint,
        (gbufferModelView*vec4(rasterPoint,1.0)).xyz,gl_FragCoord.z);
    if(solveStatus!=0 || any(isnan(solvedPoint)) || any(isinf(solvedPoint)))return hit;
    vec4 view=gbufferModelView*vec4(solvedPoint,1.0);
    vec4 clip=gbufferProjection*view;
    if(any(isnan(view)) || any(isinf(view)) || any(isnan(clip)) || any(isinf(clip)) || clip.w<=0.0)return hit;
    vec3 ndc=clip.xyz/clip.w;
    vec2 pixel=(ndc.xy*0.5+0.5)*vec2(viewWidth,viewHeight);
    float depth=0.5*(gl_DepthRange.diff*ndc.z+gl_DepthRange.near+gl_DepthRange.far);
    if(any(isnan(ndc)) || any(isinf(ndc)) || isnan(depth) || isinf(depth)
        || any(greaterThan(abs(pixel-gl_FragCoord.xy),vec2(0.01))) || depth<=0.0 || depth>=1.0)return hit;
    return WaterPrimaryHit(true,solvedPoint,view.xyz,depth);
}
