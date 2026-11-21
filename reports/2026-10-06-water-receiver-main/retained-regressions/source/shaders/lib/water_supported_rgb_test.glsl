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
