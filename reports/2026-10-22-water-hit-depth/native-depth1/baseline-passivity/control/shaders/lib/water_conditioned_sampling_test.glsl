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
