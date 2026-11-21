#ifndef AQUALUMEN_WATER_SNELL_INVERSE
#define AQUALUMEN_WATER_SNELL_INVERSE
// TEST ONLY pure inverse-node seam. Not included by production water main.
// Status: 1 supported; 0 finite unsupported orientation; -1 invalid/numeric.
// Initial implementation deliberately retains parent float arithmetic.
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
    float k2=1.0+eta*eta*(dot(view,view)-1.0);
    vec3 axis=sqrt(k2)*generatedTarget+eta*view;
    float axis2=dot(axis,axis);
    if (!WSI_finite(k2) || k2<=0.0 || !WSI_finite(axis2) || axis2<=0.0) return node;
    node.facet=axis/sqrt(axis2);
    node.facing=dot(node.facet,view);
    float targetDot=dot(generatedTarget,node.facet);
    if (node.facet.y>=0.0 || node.facing<=0.0 || targetDot>=0.0) {
        node.status=0;
        return node;
    }
    float discriminant=1.0-eta*eta*(1.0-node.facing*node.facing);
    if (!WSI_finite(discriminant) || discriminant<=0.0) return node;
    node.ray=refract(-view,node.facet,eta);
    vec3 error=abs(node.ray-sqrt(k2)*generatedTarget);
    if (!WSI_finite(node.ray) || max(max(error.x,error.y),error.z)
        >8.0*1.1920928955078125e-7*max(max(1.0,sqrt(k2)),eta)) return node;
    node.transmittedCosine=sqrt(discriminant);
    float ci=clamp(node.facing,0.0,1.0);
    float rs=(eta*ci-node.transmittedCosine)/max(eta*ci+node.transmittedCosine,1e-5);
    float rp=(ci-eta*node.transmittedCosine)/max(ci+eta*node.transmittedCosine,1e-5);
    node.transmission=1.0-0.5*(rs*rs+rp*rp);
    node.jacobian=k2*abs(targetDot)/(axis2*pow(abs(node.facet.y),3.0));
    if (!WSI_finite(node.jacobian) || !WSI_finite(node.transmission)
        || node.jacobian<=0.0 || node.transmission<0.0 || node.transmission>1.0) return node;
    node.status=1;
    return node;
}
#endif
