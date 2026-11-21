#version 330 compatibility
#ifndef AQUALUMEN_WATER_SNELL_INVERSE
#define AQUALUMEN_WATER_SNELL_INVERSE
#ifndef AQUALUMEN_SNELL_CPU_HOST
#extension GL_ARB_gpu_shader_fp64 : require
#endif
// TEST ONLY pure inverse-node seam. Not included by production water main.
// Status: 1 supported; 0 separated wrong orientation; -1 invalid/uncertain.
// Raw binary32 view is unchanged. Generated target is a direction, not a
// prescribed ray magnitude: rho accounts explicitly for its rounded norm.
// Keep the inverse internally in FP64, then cast witnesses at the boundary.
// Rounded facet32 is NOT a fresh exact-unit forward-Snell oracle at critical.
// Status0 alone never authorizes a whole-source zero/fallback policy change.
struct WaterSnellNode {
    vec3 facet;
    vec3 ray;
    float facing;
    float transmittedCosine;
    float jacobian;
    float transmission;
    int status;
};
bool WSI_finite(float value) { return !isnan(value) && !isinf(value); }
bool WSI_finite(vec3 value) {
    return WSI_finite(value.x) && WSI_finite(value.y) && WSI_finite(value.z);
}
WaterSnellNode waterSnellNode(vec3 view,vec3 generatedTarget,float eta) {
    WaterSnellNode node;
    node.facet=vec3(0.0); node.ray=vec3(0.0);
    node.facing=0.0; node.transmittedCosine=0.0;
    node.jacobian=0.0; node.transmission=0.0; node.status=-1;
    if (!WSI_finite(view) || !WSI_finite(generatedTarget)
        || !WSI_finite(eta) || eta<=1.0 || view.y>=0.0
        || generatedTarget.y<=0.0) return node;
    dvec3 v=dvec3(view),t=dvec3(generatedTarget);
    double e=double(eta),v2=dot(v,v),t2=dot(t,t);
    double k2=1.0+e*e*(v2-1.0);
    if (isnan(k2) || isinf(k2) || k2<=0.0 || t2<=0.0) return node;
    double k=sqrt(k2),rho=k/sqrt(t2);
    dvec3 outgoing=rho*t;
    dvec3 axis=outgoing+e*v;
    double axis2=dot(axis,axis);
    if (isnan(axis2) || isinf(axis2) || axis2<=0.0) return node;
    double axisLength=sqrt(axis2);
    dvec3 facet=axis/axisLength;
    double facing=dot(facet,v);
    double q=-dot(outgoing,facet);
    // Roundoff exclusion band, fixed from FP64 epsilon and inverse scale.
    // Ambiguous signs are invalid, never clamped into physical zero/support.
    // Local tested-domain safeguard, not a full interval/energy proof.
    double epsilon=double(1.0)/double(4503599627370496.0);
    double directionGuard=128.0*epsilon*(k+e*sqrt(v2))/axisLength;
    double facingGuard=directionGuard*sqrt(v2)+128.0*epsilon*abs(facing);
    double qGuard=k*directionGuard+128.0*epsilon*abs(q);
    if (facet.y>directionGuard || facing< -facingGuard || q< -qGuard) {
        node.status=0;
        return node;
    }
    if (facet.y>= -directionGuard || facing<=facingGuard || q<=qGuard) return node;
    // On the supported inverse branch D=q². Do not subtract two O(1) terms
    // to recover that tiny discriminant, or call float refract on facet32.
    dvec3 ray=-e*v+(e*facing-q)*facet;
    double ci=clamp(facing,0.0,1.0);
    // Preserve the existing Fresnel incident-cosine clamp for raw f>1.
    double fresnelCosine=facing>1.0?double(1.0):q;
    double sDen=e*ci+fresnelCosine,pDen=ci+e*fresnelCosine;
    // 1-R in positive product form, avoiding subtraction from rounded R=1.
    double transmission=2.0*e*ci*fresnelCosine*(1.0/(sDen*sDen)+1.0/(pDen*pDen));
    double ny=abs(facet.y);
    double jacobian=k*q/(axis2*ny*ny*ny);
    node.facet=vec3(facet); node.ray=vec3(ray);
    node.facing=float(facing); node.transmittedCosine=float(q);
    node.transmission=float(transmission); node.jacobian=float(jacobian);
    if (!WSI_finite(node.facet) || !WSI_finite(node.ray)
        || !WSI_finite(node.facing) || !WSI_finite(node.transmittedCosine)
        || !WSI_finite(node.jacobian) || !WSI_finite(node.transmission)
        || node.facet.y>=0.0 || node.ray.y<=0.0 || node.jacobian<=0.0
        || node.transmission<0.0 || node.transmission>1.0) return node;
    vec3 error=abs(node.ray-vec3(outgoing));
    if (max(max(error.x,error.y),error.z)
        >float(8.0)*float(1.1920928955078125e-7)*max(max(float(1.0),float(k)),eta)) return node;
    node.status=1;
    return node;
}
#endif

uniform vec3 wsView; uniform vec3 wsTarget; uniform float wsEta;
void main(){WaterSnellNode node=waterSnellNode(wsView,wsTarget,wsEta);
gl_FragData[0]=vec4(node.facet,float(node.status));
gl_FragData[1]=vec4(node.ray,node.facing);
gl_FragData[2]=vec4(node.transmittedCosine,node.transmission,node.jacobian,1.0);}
