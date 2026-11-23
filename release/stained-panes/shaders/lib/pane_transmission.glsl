// Clip one coordinate of a segment parameterized from zero to one.
// The half-open interval gives a coplanar ray a consistent owner.
vec2 paneSlab(float start,float delta,float lo,float hi) {
    if(abs(delta)<1e-8)
        return start>=lo && start<hi ? vec2(0,1) : vec2(1,0);
    vec2 t=(vec2(lo,hi)-start)/delta;
    return clamp(vec2(min(t.x,t.y),max(t.x,t.y)),0.,1.);
}
vec2 paneInterval(vec2 x,vec2 z) { return vec2(max(x.x,z.x),min(x.y,z.y)); }
float paneLength(vec2 t) { return max(t.y-t.x,0.); }

// The pane post and its four optional arms occupy the union of two rectangles
// in xz. Count the shared centre just once, even along the length of the pane.
float paneDistance(int arms,vec2 entry,vec2 delta,float travel) {
    const float lo=7./16.,hi=9./16.;
    vec2 coreX=paneSlab(entry.x,delta.x,lo,hi);
    vec2 coreZ=paneSlab(entry.y,delta.y,lo,hi);
    vec2 armsX=paneSlab(entry.x,delta.x,(arms&1)!=0?0.:lo,(arms&2)!=0?1.:hi);
    vec2 armsZ=paneSlab(entry.y,delta.y,(arms&4)!=0?0.:lo,(arms&8)!=0?1.:hi);
    vec2 xPath=paneInterval(armsX,coreZ),zPath=paneInterval(coreX,armsZ);
    return travel*(paneLength(xPath)+paneLength(zPath)-paneLength(paneInterval(xPath,zPath)));
}
vec3 paneTransmission(int word,vec3 origin,vec3 ray,float t,float end) {
    float travel=end-t;
    float distanceInGlass=paneDistance((word>>6)&15,(origin+ray*t).xz,ray.xz*travel,travel);
    return pow(lampGlass((word&63)-32),vec3(distanceInGlass));
}
