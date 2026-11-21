const int WST_order=96;
const vec2 WST_rule[96]=vec2[96](
vec2(-0.99968950388323075,0.00079679206555214482),
vec2(-0.99836437586318172,0.0018539607889468575),
vec2(-0.99598184298720926,0.0029107318179349686),
vec2(-0.99254390032376261,0.0039645543384446208),
vec2(-0.98805412632962375,0.0050142027429274511),
vec2(-0.98251726356301472,0.006058545504235552),
vec2(-0.97593917458513646,0.007096470791153827),
vec2(-0.96832682846326423,0.0081268769256986877),
vec2(-0.95968829144874257,0.0091486712307834138),
vec2(-0.95003271778443765,0.010160770535008449),
vec2(-0.93937033975275519,0.011162102099838502),
vec2(-0.92771245672230873,0.012151604671088346),
vec2(-0.91507142312089806,0.013128229566961526),
vec2(-0.9014606353158523,0.014090941772314864),
vec2(-0.88689451740242042,0.01503872102699487),
vec2(-0.87138850590929651,0.015970562902562203),
vec2(-0.85495903343460145,0.016885479864245184),
vec2(-0.83762351122818712,0.017782502316045199),
vec2(-0.81940031073793163,0.018660679627411414),
vec2(-0.80030874413914077,0.019519081140145),
vec2(-0.78036904386743322,0.020356797154333309),
vec2(-0.75960234117664749,0.021172939892191243),
vec2(-0.73803064374440008,0.021966644438744347),
vec2(-0.71567681234896763,0.022737069658329386),
vec2(-0.69256453664217155,0.023483399085926254),
vec2(-0.66871831004391613,0.024204841792364672),
vec2(-0.64416340378496706,0.024900633222483627),
vec2(-0.61892584012546858,0.025570036005349375),
vec2(-0.59303236477757204,0.02621234073567236),
vec2(-0.56651041856139717,0.02682686672559173),
vec2(-0.53938810832435746,0.02741296272602926),
vec2(-0.5116941771546677,0.027970007616848331),
vec2(-0.48345797392059636,0.028497411065085396),
vec2(-0.45470942216774302,0.028994614150555226),
vec2(-0.42547898840730053,0.029461089958167926),
vec2(-0.39579764982890858,0.029896344136328371),
vec2(-0.36569686147231362,0.030299915420827571),
vec2(-0.33520852289262543,0.030671376123669176),
vec2(-0.30436494435449635,0.031010332586313843),
vec2(-0.27319881259104917,0.031316425596861312),
vec2(-0.24174315616384001,0.03158933077072712),
vec2(-0.21003131046056719,0.031828758894411072),
vec2(-0.17809688236761861,0.032034456231992692),
vec2(-0.14597371465489695,0.032206204794030212),
vec2(-0.11369585011066592,0.032343822568575979),
vec2(-0.081297495464425565,0.032447163714064239),
vec2(-0.04881298513604973,0.032516118713868836),
vec2(-0.016276744849602967,0.03255061449236317),
vec2(0.016276744849602967,0.03255061449236317),
vec2(0.04881298513604973,0.032516118713868836),
vec2(0.081297495464425565,0.032447163714064239),
vec2(0.11369585011066592,0.032343822568575979),
vec2(0.14597371465489695,0.032206204794030212),
vec2(0.17809688236761861,0.032034456231992692),
vec2(0.21003131046056719,0.031828758894411072),
vec2(0.24174315616384001,0.03158933077072712),
vec2(0.27319881259104917,0.031316425596861312),
vec2(0.30436494435449635,0.031010332586313843),
vec2(0.33520852289262543,0.030671376123669176),
vec2(0.36569686147231362,0.030299915420827571),
vec2(0.39579764982890858,0.029896344136328371),
vec2(0.42547898840730053,0.029461089958167926),
vec2(0.45470942216774302,0.028994614150555226),
vec2(0.48345797392059636,0.028497411065085396),
vec2(0.5116941771546677,0.027970007616848331),
vec2(0.53938810832435746,0.02741296272602926),
vec2(0.56651041856139717,0.02682686672559173),
vec2(0.59303236477757204,0.02621234073567236),
vec2(0.61892584012546858,0.025570036005349375),
vec2(0.64416340378496706,0.024900633222483627),
vec2(0.66871831004391613,0.024204841792364672),
vec2(0.69256453664217155,0.023483399085926254),
vec2(0.71567681234896763,0.022737069658329386),
vec2(0.73803064374440008,0.021966644438744347),
vec2(0.75960234117664749,0.021172939892191243),
vec2(0.78036904386743322,0.020356797154333309),
vec2(0.80030874413914077,0.019519081140145),
vec2(0.81940031073793163,0.018660679627411414),
vec2(0.83762351122818712,0.017782502316045199),
vec2(0.85495903343460145,0.016885479864245184),
vec2(0.87138850590929651,0.015970562902562203),
vec2(0.88689451740242042,0.01503872102699487),
vec2(0.9014606353158523,0.014090941772314864),
vec2(0.91507142312089806,0.013128229566961526),
vec2(0.92771245672230873,0.012151604671088346),
vec2(0.93937033975275519,0.011162102099838502),
vec2(0.95003271778443765,0.010160770535008449),
vec2(0.95968829144874257,0.0091486712307834138),
vec2(0.96832682846326423,0.0081268769256986877),
vec2(0.97593917458513646,0.007096470791153827),
vec2(0.98251726356301472,0.006058545504235552),
vec2(0.98805412632962375,0.0050142027429274511),
vec2(0.99254390032376261,0.0039645543384446208),
vec2(0.99598184298720926,0.0029107318179349686),
vec2(0.99836437586318172,0.0018539607889468575),
vec2(0.99968950388323075,0.00079679206555214482));
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
    float rootX=sqrt(p.c.x),crossTerm=p.c.y/rootX,rootZ=sqrt(p.det/p.c.x),e2=p.eta*p.eta;
    for(int i=0;i<WST_order;++i) {
        float x=8.0*WST_rule[i].x,wx=8.0*WST_rule[i].y;
        float sx=p.mean.x+rootX*x,sz=p.mean.y+crossTerm*x;
        vec2 f=vec2(p.v.x*sx-p.v.y+p.v.z*sz,p.v.z*rootZ);
        vec3 h=vec3(1.0+sx*sx+sz*sz,2.0*sz*rootZ,rootZ*rootZ);
        float bound[16];int count=2;bound[0]=-8.0;bound[1]=8.0;
        WRT_roots(vec3(f,0.0),bound,count);
        WRT_roots((1.0-e2)*h+e2*WRT_product(f,f),bound,count);
        for(int horizon=0;horizon<2;++horizon) {
            vec3 w=horizon==0?vec3(0.0,1.0,0.0):p.n;
            vec2 d=vec2(w.x*sx-w.y+w.z*sz,w.z*rootZ);
            WRT_roots(2.0*WRT_product(f,d)-dot(p.v,w)*h,bound,count);
        }
        for(int j=1;j<count;++j){float value=bound[j];int k=j-1;
            while(k>=0&&bound[k]>value){bound[k+1]=bound[k];--k;}bound[k+1]=value;}
        for(int segment=0;segment<count-1;++segment) {
            float lo=bound[segment],hi=bound[segment+1];
            if(hi<=lo||WRT_reflectedNode(p,x,0.5*(lo+hi)).w==0.0)continue;
            for(int j=0;j<WST_order;++j) {
                float theta=0.5*WST_pi*(WST_rule[j].x+1.0),wt=0.5*WST_pi*WST_rule[j].y;
                float z=0.5*(lo+hi)-0.5*(hi-lo)*cos(theta);
                float wz=wt*0.5*(hi-lo)*sin(theta);
                vec4 node=WRT_reflectedNode(p,x,z);
                if(node.w<=0.0)continue; // No zero/absent ray source query.
                vec3 term=wx*wz*node.w*WRT_waterSource(node.xyz);
                vec3 adjusted=term-correction,total=sum+adjusted;correction=(total-sum)-adjusted;sum=total;
            }
        }
    }
    return sum;
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
    vec3 sum=vec3(0.0),correction=vec3(0.0);int evaluations=0;
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
                    vec3 target=vec3(r*cos(phi),u,r*sin(phi));
                    vec4 node=WST_kernel(p,target);
                    if(node.x<=0.0)continue;
                    vec3 term=wu*wp*node.x*WRT_airSource(target);
                    vec3 adjusted=term-correction,total=sum+adjusted;
                    correction=(total-sum)-adjusted;sum=total;++evaluations;
                }
            }
        }
    }
    return sum;
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
