#ifndef AQUALUMEN_DIELECTRIC_FILM
#define AQUALUMEN_DIELECTRIC_FILM
float filmFresnel(float cosine) {
    return 0.0204+0.9796*pow(1.0-clamp(cosine,0.0,1.0),5.0);
}

// GGX with height-correlated Smith masking. Return pi times the BRDF so a
// unit-albedo Lambertian response and a coated response share the emitter units.
float filmMicrofacet(vec3 n,vec3 view,vec3 light,float roughness,float emitterSlope2,float nl,float nv,float smithFloor) {
    vec3 h=view+light;
    h*=inversesqrt(max(dot(h,h),1e-12));
    float nh=clamp(dot(n,h),0.0,1.0);
    float a2=clamp(pow(roughness,4.0)+emitterSlope2,0.00012,1.0);
    float den=(1.0-nh*nh)+nh*nh*a2;
    float smith=0.5/max(nl*sqrt(a2+(1.0-a2)*nv*nv)+nv*sqrt(a2+(1.0-a2)*nl*nl),smithFloor);
    return a2*smith*filmFresnel(dot(view,h))/(den*den);
}
float filmDirectBRDF(vec3 n,vec3 view,vec3 light,float roughness,float emitterSlope2) {
    float nl=dot(n,light),nv=dot(n,view);
    if(nl<=0.0 || nv<=0.0) return 0.0;
    return filmMicrofacet(n,view,light,roughness,emitterSlope2,nl,nv,0.000001);
}

// Invert the two-flux diffuse reflectance, reduce scattering at fixed
// absorption, then solve for reflectance again. The rational form includes
// black and white without a K/S division by zero.
vec3 wetSubstrate(vec3 dry,float scatteringRatio) {
    vec3 r=clamp(dry,0.0,1.0), lost=1.0-r;
    vec3 numerator=2.0*r*max(scatteringRatio,0.0001);
    return numerator/(numerator+lost*(lost+sqrt(lost*lost+2.0*numerator)));
}
#endif
