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

#ifndef AQUALUMEN_SUPPORTED_RGB_TEST
#define AQUALUMEN_SUPPORTED_RGB_TEST
// TEST-only complete R+T single-scattering operator over declared sources.
// WST structs/functions/rule precede this file. Adapter owns source provenance:
// unknown receiver/source sets WRT_sourceKnown=false, not guessed black/sky.
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

const int WSQ_count=64;
const vec2 WSQ_proposal[64]=vec2[64](
vec2(-0.50877213478088379,0.64638912677764893),
vec2(-1.5941076278686523,0.97972244024276733),
vec2(0.13945822417736053,0.42416688799858093),
vec2(1.4791955947875977,0.75750023126602173),
vec2(-0.17521342635154724,0.090833544731140137),
vec2(-0.91362875699996948,0.53527796268463135),
vec2(0.46897423267364502,0.86861133575439453),
vec2(1.1167807579040527,0.20194464921951294),
vec2(-0.33727189898490906,0.35009279847145081),
vec2(-1.1852668523788452,0.6834261417388916),
vec2(0.30011680722236633,0.016759471967816353),
vec2(2.4550101757049561,0.46120390295982361),
vec2(-0.017657682299613953,0.7945372462272644),
vec2(-0.69682562351226807,0.1278705894947052),
vec2(0.6524854302406311,0.5723150372505188),
vec2(0.98100948333740234,0.90564835071563721),
vec2(-0.42146995663642883,0.238981693983078),
vec2(-1.3613220453262329,0.38712984323501587),
vec2(0.21907956898212433,0.72046315670013428),
vec2(1.7708355188369751,0.05379650741815567),
vec2(-0.096136778593063354,0.49824094772338867),
vec2(-0.80051594972610474,0.83157426118850708),
vec2(0.55837541818618774,0.16490761935710907),
vec2(1.2770402431488037,0.60935205221176147),
vec2(-0.25540289282798767,0.94268542528152466),
vec2(-1.0398449897766113,0.27601873874664307),
vec2(0.38317763805389404,0.32540145516395569),
vec2(-1.9737344980239868,0.65873479843139648),
vec2(0.060712646692991257,0.99206811189651489),
vec2(-0.60014152526855469,0.43651255965232849),
vec2(0.75277012586593628,0.76984590291976929),
vec2(0.91949242353439331,0.10317922383546829),
vec2(-0.46467816829681396,0.54762369394302368),
vec2(-1.467787504196167,0.88095700740814209),
vec2(0.17912690341472626,0.21429033577442169),
vec2(1.6079868078231812,0.36243847012519836),
vec2(-0.13556909561157227,0.69577181339263916),
vec2(-0.85570323467254639,0.029105151072144508),
vec2(0.51316189765930176,0.47354960441589355),
vec2(1.193079948425293,0.80688291788101196),
vec2(-0.29608923196792603,0.14021626114845276),
vec2(-1.1096220016479492,0.58466070890426636),
vec2(0.34135273098945618,0.91799402236938477),
vec2(-2.3832199573516846,0.25132736563682556),
vec2(0.021510960534214973,0.39947551488876343),
vec2(-0.64772635698318481,0.73280882835388184),
vec2(0.70174521207809448,0.066142186522483826),
vec2(1.046483039855957,0.51058661937713623),
vec2(-0.37903490662574768,0.84391999244689941),
vec2(-1.2683809995651245,0.17725330591201782),
vec2(0.25938516855239868,0.62169772386550903),
vec2(2.0015044212341309,0.95503109693527222),
vec2(-0.056853447109460831,0.28836441040039062),
vec2(-0.74766552448272705,0.33774712681770325),
vec2(0.60476064682006836,0.67108047008514404),
vec2(1.3711183071136475,0.00441379239782691),
vec2(-0.21513515710830688,0.44885823130607605),
vec2(-0.97479504346847534,0.78219157457351685),
vec2(0.42568409442901611,0.11552490293979645),
vec2(-1.7526509761810303,0.55996936559677124),
vec2(0.10000789165496826,0.89330267906188965),
vec2(-0.55387860536575317,0.22663600742816925),
vec2(0.80583488941192627,0.37478417158126831),
vec2(0.89000529050827026,0.70811748504638672));

vec3 WRT_airSource(vec3 ray);
vec3 WRT_waterSource(vec3 ray);
bool WRT_sourceKnown=true;
vec3 WRT_airIntegral(WST_Context p); // Generated from retained light partition.
vec3 WRT_lastT=vec3(0.0),WRT_lastR=vec3(0.0);
vec4 WRT_status=vec4(0.0);
vec3 WRT_seenN=vec3(0.0),WRT_seenV=vec3(0.0),WRT_seenC=vec3(0.0);
float WRT_eligible=0.0;

float WRT_reflectance(float facing,float eta) {
    float ci=clamp(facing,0.0,1.0),radicand=1.0-eta*eta*(1.0-ci*ci);
    if(radicand<=0.0)return 1.0;
    float ct=sqrt(radicand),rs=(eta*ci-ct)/(eta*ci+ct),rp=(ci-eta*ct)/(ci+eta*ct);
    return 0.5*(rs*rs+rp*rp);
}
vec4 WRT_reflectedNode(WST_Context p,float x,float z) {
    float rootX=sqrt(p.c.x),crossTerm=p.c.y/rootX,rootZ=sqrt(p.det/p.c.x);
    vec2 slope=p.mean+vec2(rootX*x,crossTerm*x+rootZ*z);
    vec3 m=normalize(vec3(slope.x,-1.0,slope.y));float facing=dot(m,p.v);
    vec3 ray=reflect(-p.v,m);
    if(facing<=0.0||ray.y>=0.0||dot(p.n,ray)<=0.0)return vec4(0.0);
    float transfer=facing/(abs(m.y)*p.projected)*WRT_reflectance(facing,p.eta)*WST_visibility(p,ray);
    return vec4(ray,exp(-0.5*(x*x+z*z))/(2.0*WST_pi)*transfer);
}
void WRT_roots(vec3 polynomial,inout float a[16],inout int count) {
    float c=polynomial.x,b=polynomial.y,q=polynomial.z;
    if(q==0.0) {
        if(b!=0.0){float root=-c/b;if(root> -8.0&&root<8.0)a[count++]=root;}
        return;
    }
    float discr=b*b-4.0*q*c;
    if(discr<0.0)return;
    float value=-0.5*(b+(b<0.0?-sqrt(discr):sqrt(discr)));
    if(value==0.0){float root=-b/(2.0*q);if(root> -8.0&&root<8.0)a[count++]=root;return;}
    float r1=value/q,r2=c/value;
    if(r1> -8.0&&r1<8.0)a[count++]=r1;
    if(r2> -8.0&&r2<8.0)a[count++]=r2;
}
vec3 WRT_product(vec2 a,vec2 b){return vec3(a.x*b.x,a.x*b.y+a.y*b.x,a.y*b.y);}
vec3 WRT_waterIntegral(WST_Context p) {
    vec3 sum=vec3(0.0),correction=vec3(0.0);
    for(int i=0;i<WSQ_count;++i) {
        float z,mass,status;
        vec4 node=WSQ_sample(p,WSQ_proposal[i].x,WSQ_proposal[i].y,1,z,mass,status);
        if(status==0.0)continue;
        vec3 term=node.w*WRT_waterSource(node.xyz);
        vec3 adjusted=term-correction,total=sum+adjusted;
        correction=(total-sum)-adjusted;sum=total;
    }
    return sum/float(WSQ_count);
}
vec3 WRT_interface(vec3 originalColor,vec3 n,vec3 v,vec3 c,bool eligible) {
    WRT_seenN=n;WRT_seenV=v;WRT_seenC=c;WRT_eligible=float(eligible);
    WRT_lastT=vec3(0.0);WRT_lastR=vec3(0.0);WRT_status=vec4(0.0);WRT_sourceKnown=true;
    WST_Context p=WST_prepare(n,v,c,1.333);
    WRT_status.x=float(p.valid);
    if(!eligible||!p.valid)return originalColor;
    // Source loss at one absent branch never rejects its supported counterpart.
    vec3 air=WRT_airIntegral(p),water=WRT_waterIntegral(p);
    bool known=WRT_sourceKnown&&WST_finite(air)&&WST_finite(water)
        &&!any(lessThan(air,vec3(0.0)))&&!any(lessThan(water,vec3(0.0)));
    WRT_status.z=float(known);
    if(!known)return originalColor; // Unproved source is not physical absence.
    WRT_lastT=air;WRT_lastR=water;WRT_status.y=1.0;
    return air+water;
}
#endif

vec3 WRT_airIntegral(WST_Context p) {
    vec3 sum=vec3(0.0),correction=vec3(0.0);
    for(int i=0;i<WSQ_count;++i) {
        float z,mass,status;
        vec4 node=WSQ_sample(p,WSQ_proposal[i].x,WSQ_proposal[i].y,0,z,mass,status);
        if(status==0.0)continue;
        vec3 term=node.w*WRT_airSource(node.xyz);
        vec3 adjusted=term-correction,total=sum+adjusted;
        correction=(total-sum)-adjusted;sum=total;
    }
    return sum/float(WSQ_count);
}

#ifndef AQUALUMEN_SUPPORTED_SOURCES_TEST
#define AQUALUMEN_SUPPORTED_SOURCES_TEST
// TEST adapter, not installed production code. Tracers/stock sky precede this.
// Known radiance, physical absence and unobserved geometry are distinct.
// Proxies retain the legacy convention only when explicitly permitted; their
// use is counted, and does not establish actual offscreen light transport.
vec3 WSA_position,WSA_origin,WSA_scatter,WSA_cave;
float WSA_access=0.0;
bool WSA_allowProxies=true,WSA_proxyUsed=false;
float WSA_airSky=0.0,WSA_airOpaque=0.0,WSA_airUnknown=0.0;
float WSA_reflectionHits=0.0,WSA_reflectionMisses=0.0;
vec4 WSA_sunLedger=vec4(0.0),WSA_moonLedger=vec4(0.0);
vec3 WSA_solar=vec3(0.0),WSA_lunar=vec3(0.0);

vec3 WSA_checked(vec3 radiance) {
    if(!WST_finite(radiance)||any(lessThan(radiance,vec3(0.0)))) {
        WRT_sourceKnown=false;
        return vec3(0.0);
    }
    return radiance;
}
int WSA_airTrace(vec3 ray,out vec2 uv) {
    if(!WST_finite(ray)||ray.y<=0.0||dot(ray,ray)<1e-6) {
        WRT_sourceKnown=false;uv=vec2(0.0);return -1;
    }
    float path=48.0,confidence=0.0;int kind=0;
    uv=refractionTrace(WSA_origin,mat3(gbufferModelView)*ray,
        gl_FragCoord.xy/vec2(viewWidth,viewHeight),48.0,48.0,false,
        WSA_position.y+cameraPosition.y,path,kind,confidence);
    if(kind==2)WSA_airSky+=1.0;
    else if(kind==1)WSA_airOpaque+=1.0;
    else {WSA_airUnknown+=1.0;WSA_proxyUsed=true;
        if(!WSA_allowProxies)WRT_sourceKnown=false;}
    return kind;
}
vec3 WRT_airSource(vec3 ray) {
    vec2 uv;int kind=WSA_airTrace(ray,uv);
    if(kind<0)return vec3(0.0);
    // C4 is a real visible receiver's existing shaded radiance. Do not add a
    // separate solar disk to that receiver. Eye-water attenuation occurs later.
    if(kind==1)return WSA_checked(texture(colortex4,uv).rgb);
    vec3 sky=sampleSky(colortex6,ray);
    return WSA_checked(kind==2?sky:mix(WSA_cave,sky,WSA_access*WSA_access));
}
vec3 WRT_waterSource(vec3 ray) {
    if(!WST_finite(ray)||ray.y>=0.0||dot(ray,ray)<1e-6) {
        WRT_sourceKnown=false;return vec3(0.0);
    }
    // Forward reflected ray has the retained raw view length. Its half-vector
    // recovers the generating facet; no raw view/normal/covariance repair.
    vec3 axis=WRT_seenV+ray;
    if(dot(axis,axis)<=0.0){WRT_sourceKnown=false;return vec3(0.0);}
    vec3 facet=axis/sqrt(dot(axis,axis));
    vec4 hit=reflectionTrace(WSA_origin+mat3(gbufferModelView)*facet*0.06,
        mat3(gbufferModelView)*ray,WSA_scatter,false,WSA_position.y);
    if(hit.a>0.0) {
        WSA_reflectionHits+=1.0;
        vec3 trans=waterTransmission(hit.a);
        return WSA_checked(hit.rgb*trans+WSA_scatter*(1.0-trans));
    }
    WSA_reflectionMisses+=1.0;WSA_proxyUsed=true;
    if(!WSA_allowProxies)WRT_sourceKnown=false;
    return WSA_checked(WSA_scatter);
}
float WSA_cap(WST_Context p,vec3 axis,float radius,out vec4 ledger) {
    ledger=vec4(0.0);
    float axis2=dot(axis,axis);
    if(!WST_finite(axis)||axis2<=0.0||radius<=0.0) {
        WRT_sourceKnown=false;return 0.0;
    }
    // Normalize generated source directions only, not observed n/v.
    axis=axis/sqrt(axis2);
    vec3 auxiliary=abs(axis.y)<0.95?vec3(0.0,1.0,0.0):vec3(1.0,0.0,0.0);
    vec3 tangent=normalize(cross(axis,auxiliary)),bitangent=cross(axis,tangent);
    float capDelta=2.0*pow(sin(0.5*radius),2.0);
    const float radial[4]=float[4](0.06943184420297371,0.33000947820757187,
        0.6699905217924281,0.9305681557970262);
    const float weights[4]=float[4](0.17392742256872687,0.32607257743127305,
        0.32607257743127305,0.17392742256872687);
    float sum=0.0,correction=0.0;
    for(int r=0;r<4;++r)for(int j=0;j<12;++j) {
        float offset=capDelta*radial[r],cosine=1.0-offset;
        float sine=sqrt(offset*(2.0-offset)),phi=TAU*(float(j)+0.5)/12.0;
        vec3 target=normalize(cosine*axis+sine*(cos(phi)*tangent+sin(phi)*bitangent));
        vec4 node=WST_kernel(p,target);
        ledger.w+=1.0;
        if(node.y==0.0){ledger.x+=1.0;continue;}
        ledger.y+=1.0;
        if(!WST_finite(node.xyz)||isnan(node.w)||isinf(node.w)||node.x<0.0) {
            WRT_sourceKnown=false;continue;
        }
        if(node.x==0.0)continue;
        vec2 uv;int kind=WSA_airTrace(target,uv);
        // A known opaque receiver blocks this sharp source; its C4 radiance
        // already enters the diffuse/receiver integral. Unknown is a counted
        // access proxy, never a declaration of unobstructed physical sky.
        if(kind==1){ledger.z+=1.0;continue;}
        if(kind<0)continue;
        float access=kind==2?1.0:WSA_access*WSA_access;
        float term=weights[r]*node.x*access;
        float adjusted=term-correction,total=sum+adjusted;
        correction=(total-sum)-adjusted;sum=total;
    }
    return sum*(capDelta*TAU/12.0);
}
vec3 WSA_interface(vec3 originalColor,vec3 n,vec3 v,vec3 c,
    vec3 position,vec3 origin,float access,vec3 cave,vec3 scatter,
    bool eligible,bool allowProxies) {
    WSA_position=position;WSA_origin=origin;WSA_access=access;
    WSA_cave=cave;WSA_scatter=scatter;WSA_allowProxies=allowProxies;
    WSA_proxyUsed=false;WSA_airSky=0.0;WSA_airOpaque=0.0;WSA_airUnknown=0.0;
    WSA_reflectionHits=0.0;WSA_reflectionMisses=0.0;
    WSA_sunLedger=vec4(0.0);WSA_moonLedger=vec4(0.0);
    WSA_solar=vec3(0.0);WSA_lunar=vec3(0.0);
    WST_Context p=WST_prepare(n,v,c,1.333);
    vec3 result=WRT_interface(originalColor,n,v,c,eligible);
    if(!eligible||!p.valid)return originalColor;
    if(WRT_status.y!=1.0)return originalColor;
    if(earthAtmosphere()) {
        vec3 sun=sunDirection();
        vec3 beam=SOLAR*cachedSolarTransmission(colortex6)*(1.0-0.85*rainStrength);
        beam=WSA_checked(beam);
        if(any(greaterThan(beam,vec3(0.0)))) {
            float solarIntegral=WSA_cap(p,sun,SUN_ANGULAR_RADIUS,WSA_sunLedger);
            WSA_solar=beam*(solarIntegral/(PI*pow(sin(SUN_ANGULAR_RADIUS),2.0)));
        }
        // Retain fixed full-Moon source amplitude/radius, not derivative AA.
        // Lunar phase, absolute lunar calibration and pixel footprint are open.
        vec3 lunarRadiance=vec3(0.12,0.16,0.24)*smoothstep(0.0,0.08,-sun.y);
        if(any(greaterThan(lunarRadiance,vec3(0.0))))
            WSA_lunar=lunarRadiance*WSA_cap(p,-sun,0.0045,WSA_moonLedger);
    }
    result+=WSA_solar+WSA_lunar;
    if(!WRT_sourceKnown||!WST_finite(result)||any(lessThan(result,vec3(0.0)))) {
        WRT_status.yz=vec2(0.0);WRT_lastT=vec3(0.0);WRT_lastR=vec3(0.0);
        return originalColor;
    }
    WRT_lastT+=WSA_solar+WSA_lunar;
    return result;
}
#endif
