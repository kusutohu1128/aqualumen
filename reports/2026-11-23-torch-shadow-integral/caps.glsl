// A cuboid frequently cuts the emitter with just one straight edge. Two
// such silhouettes need only two clipped chords for their common area.
float clippedChord(vec3 p,vec3 q,vec2 pole) {
    vec2 tangent=vec2(p.y,-p.x);
    float extent=sqrt(max(0.,(1.-p.z)*(1.+p.z)));
    vec2 span=vec2(-extent,extent);
    vec2 sumNormal=p.xy+q.xy,diff=p.xy-q.xy;
    float sum2=dot(sumNormal,sumNormal);
    float base=sum2<2.?q.z+p.z-.5*p.z*sum2:q.z-p.z+.5*p.z*dot(diff,diff);
    rimClip(base,dot(sum2<2.?sumNormal:-diff,tangent),span);
    if(span.y<=span.x) return 0.;
    vec2 foot=-p.z*p.xy-pole;
    vec2 a=foot+span.x*tangent,b=foot+span.y*tangent;
    float chord=span.y-span.x;
    return p.z*chord-2.*atan((p.z+dot(pole,p.xy))*chord,dot(a,b));
}

float twoCaps(vec3 p,vec3 q,float a,float b) {
    vec2 diff=p.xy-q.xy;
    float width=p.z-q.z;
    if(dot(diff,diff)<=width*width+1e-12) return min(a,b);
    vec2 sumNormal=p.xy+q.xy;
    float overlap=p.z+q.z;
    if(dot(sumNormal,sumNormal)<=overlap*overlap+1e-12)
        return overlap>=0.?0.:max(0.,a+b-1.);
    vec2 pole=p.z<q.z?-p.xy:-q.xy;
    float sharedArea=(clippedChord(p,q,pole)+clippedChord(q,p,pole))/6.283185307;
    return clamp(a+b-1.+sharedArea,max(0.,a+b-1.),min(a,b));
}
