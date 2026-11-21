#version 400 compatibility
uniform sampler2D inputNodes;
const int WST_order=2;
const vec2 WST_rule[2]=vec2[2](
vec2(-0.57735026918962573,1.0000000000000004),
vec2(0.57735026918962573,1.0000000000000004));
#ifndef AQUALUMEN_WATER_SUPPORTED_TRANSMISSION_TEST
#define AQUALUMEN_WATER_SUPPORTED_TRANSMISSION_TEST
// TEST ONLY. No production include, no survivor-mass normalization.
// Correlated Gaussian world-horizontal slopes; height-correlated Smith closure.
// Legacy radiance units, black water reflection, constant upward air source.
// Quadrature rules WST_order/WST_rule are supplied by the TEST source builder.
const float WST_pi=3.14159265358979323846;
struct WST_Context {
    vec3 n; vec3 v; vec3 c;
    vec2 mean; float det; float projected; float eta; float k; float k2;
    bool valid;
};
bool WST_finite(vec3 a) {return !any(isnan(a))&&!any(isinf(a));}
WST_Context WST_prepare(vec3 n,vec3 v,vec3 c,float eta) {
    WST_Context p;
    p.n=n;p.v=v;p.c=c;p.eta=eta;
    p.det=c.x*c.z-c.y*c.y;
    p.valid=WST_finite(n)&&WST_finite(v)&&WST_finite(c)
        &&!isnan(eta)&&!isinf(eta)&&eta>1.0
        &&abs(dot(n,n)-1.0)<=2e-5&&abs(dot(v,v)-1.0)<=2e-5
        &&n.y< -0.5&&v.y<0.0&&c.x>0.0&&c.z>0.0&&p.det>0.0;
    p.mean=vec2(0.0);p.projected=0.0;p.k2=0.0;p.k=0.0;
    if(!p.valid)return p;
    p.mean=-n.xz/n.y;
    p.projected=dot(n,v)/abs(n.y);
    // Raw input norm is retained; no view normalization repair.
    p.k2=1.0+eta*eta*(dot(v,v)-1.0);
    p.valid=p.projected>1e-5&&p.k2>0.0;
    if(p.valid)p.k=sqrt(p.k2);
    return p;
}
float WST_erfcPositive(float x) {
    // Authored evaluation of A&S 7.1.26, page299; x>=0. Not an exact erfc.
    // Published approximation bound is not a floating-point shader error bound.
    float t=1.0/(1.0+0.3275911*x);
    return t*(0.254829592+t*(-0.284496736+t*(1.421413741
        +t*(-1.453152027+t*1.061405429))))*exp(-x*x);
}
float WST_lambda(WST_Context p,vec3 w) {
    float d=abs(w.y-dot(w.xz,p.mean));
    float variance=p.c.x*w.x*w.x+2.0*p.c.y*w.x*w.z+p.c.z*w.z*w.z;
    if(variance==0.0)return 0.0;
    float a=d/sqrt(variance);
    return max(0.0,exp(-0.5*a*a)/(a*sqrt(2.0*WST_pi))
        -0.5*WST_erfcPositive(a/sqrt(2.0)));
}
float WST_visibility(WST_Context p,vec3 t) {
    if(abs(t.y-dot(t.xz,p.mean))==0.0)return 0.0;
    return 1.0/(1.0+WST_lambda(p,p.v)+WST_lambda(p,t));
}
// kernel / supported / G2 / slope-to-solid-angle Jacobian.
vec4 WST_kernel(WST_Context p,vec3 t) {
    if(!p.valid||!WST_finite(t)||abs(dot(t,t)-1.0)>2e-5||t.y<=0.0)return vec4(0.0);
    float b=dot(p.v,t);
    if(p.k*t.y+p.eta*p.v.y>=0.0||p.k+p.eta*b>=0.0
        ||dot(p.n,t)>=0.0)return vec4(0.0);
    vec3 axis=p.k*t+p.eta*p.v;
    float axis2=dot(axis,axis);
    if(axis2<=0.0)return vec4(0.0);
    vec3 m=axis/sqrt(axis2);
    float facing=dot(m,p.v),tm=dot(t,m);
    if(m.y>=0.0||facing<=0.0||tm>=0.0)return vec4(0.0);
    // Stable inverse critical cosine; do not subtract to reconstruct ct².
    float ct=-p.k*tm,ci=clamp(facing,0.0,1.0);
    if(ci!=facing)ct=1.0; // Existing raw f>1 Fresnel convention retained.
    float sd=p.eta*ci+ct,pd=ci+p.eta*ct;
    float transmission=2.0*p.eta*ci*ct*(1.0/(sd*sd)+1.0/(pd*pd));
    vec2 delta=-m.xz/m.y-p.mean;
    float density=exp(-0.5*(p.c.z*delta.x*delta.x-2.0*p.c.y*delta.x*delta.y
        +p.c.x*delta.y*delta.y)/p.det)/(2.0*WST_pi*sqrt(p.det));
    float projected=facing/(abs(m.y)*p.projected);
    float g=WST_visibility(p,t);
    float j=p.k2*(-tm)/(axis2*pow(abs(m.y),3.0));
    return vec4(density*projected*transmission*g*j,1.0,g,j);
}
void WST_sort(inout float a[6],int count) {
    for(int i=1;i<count;++i) {
        float value=a[i];int j=i-1;
        while(j>=0&&a[j]>value){a[j+1]=a[j];--j;}
        a[j+1]=value;
    }
}
// Integrate every supported direction individually; never reject the integral
// because one direction is absent. CPU reference uses an independent forward
// slope-domain integral in addition to this inverse light-domain construction.
vec3 WST_constantAir(WST_Context p) {
    if(!p.valid)return vec3(0.0);
    float bound[6];int count=2;
    float upper=min(1.0,-p.eta*p.v.y/p.k);
    bound[0]=0.0;bound[1]=upper;
    float v2=dot(p.v,p.v),horizontal=length(p.v.xz),a=p.k/p.eta;
    float discr=horizontal*sqrt(max(0.0,v2-a*a));
    for(int signIndex=0;signIndex<2;++signIndex) {
        float root=(-a*p.v.y+(signIndex==0?-discr:discr))/v2;
        if(root>0.0&&root<upper)bound[count++]=root;
    }
    float macro=length(p.n.xz)/length(p.n);
    if(macro>0.0&&macro<upper)bound[count++]=macro;
    WST_sort(bound,count);
    float center=horizontal>0.0?atan(-p.v.z,-p.v.x):0.0;
    float na=p.n.x*cos(center)+p.n.z*sin(center);
    float nb=-p.n.x*sin(center)+p.n.z*cos(center);
    float amplitude=length(vec2(na,nb));
    float sum=0.0,correction=0.0;int evaluations=0;
    for(int interval=0;interval<count-1;++interval) {
        float lo=bound[interval],hi=bound[interval+1];
        if(hi<=lo)continue;
        for(int i=0;i<WST_order;++i) {
            float u=0.5*((hi-lo)*WST_rule[i].x+hi+lo);
            float wu=0.5*(hi-lo)*WST_rule[i].y,r=sqrt(max(0.0,1.0-u*u));
            float halfWidth=WST_pi;
            if(horizontal*r==0.0) {
                if(a+p.v.y*u>=0.0)continue;
            } else {
                float threshold=(a+p.v.y*u)/(horizontal*r);
                if(threshold>=1.0)continue;
                if(threshold> -1.0)halfWidth=acos(threshold);
            }
            float arc[6];int arcCount=2;
            arc[0]=-halfWidth;arc[1]=halfWidth;
            if(amplitude*r>0.0) {
                float ratio=-p.n.y*u/(amplitude*r);
                if(ratio> -1.0&&ratio<1.0) {
                    float offset=atan(nb,na),angle=acos(ratio);
                    for(int j=-2;j<=2;++j)for(int s=0;s<2;++s) {
                        float root=offset+(s==0?-angle:angle)+2.0*WST_pi*float(j);
                        if(root> -halfWidth&&root<halfWidth)arc[arcCount++]=root;
                    }
                }
            }
            WST_sort(arc,arcCount);
            for(int segment=0;segment<arcCount-1;++segment) {
                float pl=arc[segment],ph=arc[segment+1],mid=0.5*(pl+ph);
                if(p.n.y*u+r*(na*cos(mid)+nb*sin(mid))>=0.0)continue;
                for(int j=0;j<WST_order;++j) {
                    float phi=center+0.5*((ph-pl)*WST_rule[j].x+ph+pl);
                    float wp=0.5*(ph-pl)*WST_rule[j].y;
                    float term=wu*wp*WST_kernel(p,vec3(r*cos(phi),u,r*sin(phi))).x;
                    float adjusted=term-correction,total=sum+adjusted;
                    correction=(total-sum)-adjusted;sum=total;++evaluations;
                }
            }
        }
    }
    return vec3(sum,float(evaluations),1.0);
}
#endif
#ifndef AQUALUMEN_CONDITIONED_SAMPLING_TEST
#define AQUALUMEN_CONDITIONED_SAMPLING_TEST
// TEST only. WST context/Smith functions precede this file. Same physical
// Gaussian; orthogonal proposal axes, analytic support and probability weights.
// CDF uses incomplete-gamma series/continued fraction, not an exact primitive.
vec4 WSQ_basis(WST_Context p) {
    float h=1.0+dot(p.mean,p.mean),f=dot(p.v.xz,p.mean)-p.v.y;
    vec2 gradient=(p.v.xz*h-f*p.mean)/(h*sqrt(h));
    float rx=sqrt(p.c.x),cr=p.c.y/rx,rz=sqrt(p.det/p.c.x);
    vec2 g=vec2(rx*gradient.x+cr*gradient.y,rz*gradient.y);
    float norm=length(g);
    return norm==0.0?vec4(1.0,0.0,0.0,1.0):vec4(g.y,g.x,-g.x,g.y)/norm;
}
vec4 WSQ_node(WST_Context p,vec4 q,float x,float z,int branch) {
    vec2 original=vec2(q.x*x+q.y*z,q.z*x+q.w*z);
    float rx=sqrt(p.c.x),cr=p.c.y/rx,rz=sqrt(p.det/p.c.x);
    vec2 slope=p.mean+vec2(rx*original.x,cr*original.x+rz*original.y);
    vec3 m=normalize(vec3(slope.x,-1.0,slope.y));float f=dot(m,p.v);
    if(f<=0.0)return vec4(0.0);
    float radicand=1.0-p.eta*p.eta*(1.0-f*f);
    vec3 target;float coefficient;
    float ci=clamp(f,0.0,1.0),ciRadicand=1.0-p.eta*p.eta*(1.0-ci*ci);
    if(branch==0) {
        if(radicand<=0.0)return vec4(0.0);
        target=(-p.eta*p.v+(p.eta*f-sqrt(radicand))*m)/p.k;
        if(target.y<=0.0||dot(p.n,target)>=0.0)return vec4(0.0);
        float ct=ciRadicand<=0.0?0.0:sqrt(ciRadicand);
        float a=p.eta*ci+ct,b=ci+p.eta*ct;
        coefficient=2.0*p.eta*ci*ct*(1.0/(a*a)+1.0/(b*b));
    } else {
        target=reflect(-p.v,m);
        if(target.y>=0.0||dot(p.n,target)<=0.0)return vec4(0.0);
        coefficient=1.0;
        if(ciRadicand>0.0) {
            float ct=sqrt(ciRadicand),rs=(p.eta*ci-ct)/(p.eta*ci+ct),rp=(ci-p.eta*ct)/(ci+p.eta*ct);
            coefficient=0.5*(rs*rs+rp*rp);
        }
    }
    float transfer=f/(abs(m.y)*p.projected)*coefficient*WST_visibility(p,target);
    return vec4(target,transfer);
}
vec3 WSQ_product(vec2 a,vec2 b) {return vec3(a.x*b.x,a.x*b.y+a.y*b.x,a.y*b.y);}
void WSQ_roots(vec3 p,inout float bounds[20],inout int count) {
    if(p.z==0.0) {
        if(p.y!=0.0){float root=-p.x/p.y;if(root> -8.0&&root<8.0)bounds[count++]=root;}
        return;
    }
    float discriminant=p.y*p.y-4.0*p.z*p.x;
    if(discriminant<0.0)return;
    float a=-0.5*(p.y+(p.y<0.0?-sqrt(discriminant):sqrt(discriminant)));
    if(a==0.0){float root=-p.y/(2.0*p.z);if(root> -8.0&&root<8.0)bounds[count++]=root;return;}
    float r1=a/p.z,r2=p.x/a;
    if(r1> -8.0&&r1<8.0)bounds[count++]=r1;
    if(r2> -8.0&&r2<8.0)bounds[count++]=r2;
}
void WSQ_partition(WST_Context p,vec4 q,float x,int branch,out float bounds[20],out int count) {
    float rx=sqrt(p.c.x),cr=p.c.y/rx,rz=sqrt(p.det/p.c.x);
    vec2 first=vec2(rx*q.x,cr*q.x+rz*q.z),second=vec2(rx*q.y,cr*q.y+rz*q.w);
    vec2 slope=p.mean+first*x;
    vec2 f=vec2(dot(p.v.xz,slope)-p.v.y,dot(p.v.xz,second));
    vec3 h=vec3(1.0+dot(slope,slope),2.0*dot(slope,second),dot(second,second));
    float e2=p.eta*p.eta;count=2;bounds[0]=-8.0;bounds[1]=8.0;
    WSQ_roots(vec3(f,0.0),bounds,count);
    WSQ_roots((1.0-e2)*h+e2*WSQ_product(f,f),bounds,count);
    for(int horizon=0;horizon<2;++horizon) {
        vec3 w=horizon==0?vec3(0.0,1.0,0.0):p.n;
        vec2 d=vec2(dot(w.xz,slope)-w.y,dot(w.xz,second));float a=dot(p.v,w);
        if(branch==0) {
            WSQ_roots(vec3(d,0.0),bounds,count);
            WSQ_roots(WSQ_product(f,d)-a*h,bounds,count);
            WSQ_roots(e2*a*a*h-2.0*e2*a*WSQ_product(f,d)+(e2-1.0)*WSQ_product(d,d),bounds,count);
        } else WSQ_roots(2.0*WSQ_product(f,d)-a*h,bounds,count);
    }
    for(int i=1;i<count;++i){float value=bounds[i];int j=i-1;
        while(j>=0&&bounds[j]>value){bounds[j+1]=bounds[j];--j;}bounds[j+1]=value;}
}
float WSQ_tail(float z) {
    // Q(1/2,z^2/2)/2. Authored evaluation of NIST DLMF 8.7.1 and 8.9.2,
    // with erfc/incomplete-gamma relation 7.11.2. Positive series near zero;
    // backward continued fraction in the tail avoids subtracting from one.
    // Fixed truncations have selected-node tests, not interval certification.
    float t=0.5*z*z;
    if(z<2.0) {
        float term=2.0,sum=term;
        for(int i=1;i<=18;++i){term*=t/(float(i)+0.5);sum+=term;}
        return 0.5*(1.0-exp(-t)*sqrt(t/WST_pi)*sum);
    }
    float denominator=1.0;
    for(int i=48;i>=1;--i)denominator=1.0+(0.5*float(i)/t)/denominator;
    return 0.5*exp(-t)/(sqrt(WST_pi*t)*denominator);
}
float WSQ_mass(float lo,float hi) {
    if(hi<=lo)return 0.0;
    if(lo>=0.0)return max(0.0,WSQ_tail(lo)-WSQ_tail(hi));
    if(hi<=0.0)return max(0.0,WSQ_tail(-hi)-WSQ_tail(-lo));
    return max(0.0,1.0-WSQ_tail(hi)-WSQ_tail(-lo));
}
vec4 WSQ_sample(WST_Context p,float x,float u,int branch,out float z,out float mass,out float status) {
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
    if(mass<=0.0)return vec4(0.0); // Individual physically absent branch.
    float value=u*mass;
    for(int i=0;i<count-1;++i) {
        float interval=probability[i];if(interval<=0.0)continue;
        if(value>=interval){value-=interval;continue;}
        float lo=bounds[i],hi=bounds[i+1],origin=lo;
        for(int iteration=0;iteration<24;++iteration) {
            float mid=0.5*(lo+hi);
            if(WSQ_mass(origin,mid)<value)lo=mid;else hi=mid;
        }
        z=0.5*(lo+hi);vec4 node=WSQ_node(p,q,x,z,branch);
        if(node.w<=0.0)return vec4(0.0);
        status=1.0;
        // q(z|S)=phi(z)/mass: keep its known probability, not survivor count.
        return vec4(node.xyz,node.w*mass);
    }
    return vec4(0.0);
}
#endif
// Independently generated DCT coefficients; no borrowed implementation.
const float WSF_central[13]=float[13](1.4912989404744901,0.60175630341082997,-0.0091705595000810079,-0.0049626353267663691,0.00091537967000788892,-3.8895627570348566e-06,-2.4202599405015826e-05,3.2665715927475249e-06,2.7758889798026399e-07,-1.3023363005535218e-07,8.1046434080919846e-09,2.8624385522526869e-09,-5.975090718696955e-10);
float WSF_centralRatio(float variable) {
    float t=(2.0*variable-(0+5))/(5-0);
    float b1=0.0,b2=0.0;
    for(int k=12;k>=1;--k){float b0=2.0*t*b1-b2+WSF_central[k];b2=b1;b1=b0;}
    return t*b1-b2+WSF_central[0];
}
const float WSF_tail[17]=float[17](3.9631038613347123,1.8936394670176189,0.0052331991807146221,-0.0029627359892262254,0.0012829650810762263,-0.00054454470477623628,0.00022213736261190246,-7.9990254210842452e-05,2.2293078888611191e-05,-3.0874591924847966e-06,-1.1168622065110291e-06,1.0176153639551255e-06,-4.0075780520607441e-07,7.9681177791402435e-08,8.845965757803536e-09,-1.3597973753387018e-08,5.3464425078982025e-09);
float WSF_tailRatio(float variable) {
    float t=(2.0*variable-(2.2360679774997898+6))/(6-2.2360679774997898);
    float b1=0.0,b2=0.0;
    for(int k=16;k>=1;--k){float b0=2.0*t*b1-b2+WSF_tail[k];b2=b1;b1=b0;}
    return t*b1-b2+WSF_tail[0];
}
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

void main(){
    ivec2 p=ivec2(gl_FragCoord.xy);
    vec4 a=texelFetch(inputNodes,ivec2(p.x*3,p.y),0);
    vec4 b=texelFetch(inputNodes,ivec2(p.x*3+1,p.y),0);
    vec4 d=texelFetch(inputNodes,ivec2(p.x*3+2,p.y),0);
    float value;bool valid=WSF_inverseTail(a.w,value);
    gl_FragData[0]=vec4(value,float(valid),0.0,0.0);
    gl_FragData[1]=a;gl_FragData[2]=b;gl_FragData[3]=d;
    gl_FragData[4]=vec4(0.0);gl_FragData[5]=vec4(0.0);
    gl_FragData[6]=vec4(0.0);gl_FragData[7]=vec4(0.0);
}
