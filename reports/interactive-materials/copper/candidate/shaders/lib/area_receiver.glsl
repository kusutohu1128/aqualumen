// A float32 exactly represents each pair of twelve-bit fields.
float areaPackPair(vec2 v) {
    vec2 q=round(clamp(v,0.,1.)*4095.);
    return q.x+4096.*q.y;
}
vec2 areaUnpackPair(float v) {
    return vec2(mod(v,4096.),floor(v/4096.))/4095.;
}
vec2 areaSign(vec2 p) { return mix(vec2(-1),vec2(1),greaterThanEqual(p,vec2(0))); }
float areaEncodeNormal(vec3 n) {
    vec3 a=abs(n);
    int k=a.x>a.y && a.x>a.z?0:(a.y>a.z?1:2);
    if(a[k]>.999999 && dot(n,n)-a[k]*a[k]<1e-8) return -float(1+2*k+int(n[k]>0.));
    n/=a.x+a.y+a.z;
    vec2 oct=n.z>=0.?n.xy:(1.-abs(n.yx))*areaSign(n.xy);
    return areaPackPair(.5+.5*oct);
}
vec3 areaDecodeNormal(float v) {
    if(v<0.) {
        int f=int(-v)-1;
        vec3 n=vec3(0);n[f/2]=(f%2==0)?-1.:1.;
        return n;
    }
    vec2 oct=2.*areaUnpackPair(v)-1.;
    vec3 n=vec3(oct,1.-abs(oct.x)-abs(oct.y));
    if(n.z<0.) n.xy=(1.-abs(n.yx))*areaSign(n.xy);
    return normalize(n);
}
