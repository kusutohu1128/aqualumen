#ifndef AQUALUMEN_CONDITIONED_INVERSE_TEST
#define AQUALUMEN_CONDITIONED_INVERSE_TEST
// TEST only; own generated Chebyshev ratios precede this file. Same retained
// support, CDF masses, raw model and known probability weights as WSQ_sample.
bool WSF_inverseTail(float probability,out float result) {
    result=0.0;
    if(isnan(probability)||isinf(probability)||probability<=0.0||probability>0.5)return false;
    float w=-log(4.0*probability*(1.0-probability));
    if(w>36.0||isnan(w)||isinf(w))return false;
    float ratio=w<=5.0?WSF_centralRatio(w):WSF_tailRatio(sqrt(w));
    result=sqrt(2.0)*(1.0-2.0*probability)*ratio;
    return !isnan(result)&&!isinf(result)&&result>=0.0;
}
vec4 WSF_sample(WST_Context p,float x,float u,int branch,out float z,out float mass,out float status) {
    z=0.0;mass=0.0;status=0.0;
    if(!p.valid||isnan(x)||isinf(x)||isnan(u)||isinf(u)||abs(x)>=8.0||u<=0.0||u>=1.0)return vec4(0.0);
    vec4 q=WSQ_basis(p);float bounds[20];int count;
    WSQ_partition(p,q,x,branch,bounds,count);
    float probability[20];
    for(int i=0;i<count-1;++i) {
        float lo=bounds[i],hi=bounds[i+1];
        probability[i]=hi>lo&&WSQ_node(p,q,x,0.5*(lo+hi),branch).w>0.0?WSQ_mass(lo,hi):0.0;
        mass+=probability[i];
    }
    if(mass<=0.0)return vec4(0.0); // Physical absence, no source query.
    float value=u*mass;
    for(int i=0;i<count-1;++i) {
        float interval=probability[i];if(interval<=0.0)continue;
        if(value>=interval){value-=interval;continue;}
        float lo=bounds[i],hi=bounds[i+1];
        // Single-interval cancellation: recover the original generated u,
        // rather than (u*mass)/mass rounding to a closed endpoint.
        float fraction=mass==interval?u:value/interval;
        float small;bool positive;
        if(lo>=0.0) {
            small=(1.0-fraction)*WSQ_tail(lo)+fraction*WSQ_tail(hi);positive=true;
        } else if(hi<=0.0) {
            small=(1.0-fraction)*WSQ_tail(-lo)+fraction*WSQ_tail(-hi);positive=false;
        } else {
            float left=WSQ_tail(-lo)+value;
            positive=left>0.5;
            small=positive?WSQ_tail(hi)+(interval-value):left;
        }
        float absoluteZ;
        if(!WSF_inverseTail(small,absoluteZ)) {status=-1.0;return vec4(0.0);}
        z=positive?absoluteZ:-absoluteZ;
        // Numerical uncertainty is not a missing physical contribution.
        if(z<lo||z>hi){status=-1.0;return vec4(0.0);}
        vec4 node=WSQ_node(p,q,x,z,branch);
        if(node.w<=0.0){status=-1.0;return vec4(0.0);}
        status=1.0;return vec4(node.xyz,node.w*mass);
    }
    status=-1.0;return vec4(0.0);
}
#endif
