#include "/lib/canopy_columns.glsl"
uniform usampler2D aqualumenRawIndex;
uniform sampler2D colortex11;

// Integrate the part of the ray inside leaves in one vertical bit-column.
// Voxel intersections are exact for captured full blocks. Leaf sheets use
// their mean volume extinction at this distance.
float canopyColumnLeaves(ivec2 column,int band,float y0,float y1,inout bool blocked) {
    int first=clamp(int(floor(y0)),0,31),last=clamp(int(ceil(y1))-1,first,31);
    uint mask=(0xffffffffu<<uint(first))&(0xffffffffu>>uint(31-last));
    uint solid=texelFetch(aqualumenRawIndex,canopyMaskAddress(column,band,0),0).r;
    if((solid&mask)!=0u) {blocked=true;return 0.;}
    uint leaves=texelFetch(aqualumenRawIndex,canopyMaskAddress(column,band,1),0).r&mask;
    float height=float(bitCount(leaves));
    if((leaves&(1u<<uint(first)))!=0u) height-=y0-float(first);
    if((leaves&(1u<<uint(last)))!=0u) height-=float(last+1)-y1;
    return max(height,0.);
}
float canopyColumnRay(vec3 p,vec3 d) {
    vec3 start=p+.002*d;
    ivec2 c=ivec2(floor(start.xz)),stepCell=ivec2(sign(d.xz));
    vec2 stride=1./abs(d.xz);
    vec2 edge=(vec2(c)+step(vec2(0),d.xz)-start.xz)/d.xz;
    float t=0.,leafLength=0.;
    for(int j=0;j<19;j++) {
        float leave=min(11.998,min(edge.x,edge.y));
        if(leave>t) {
            float y0=start.y+t*d.y,y1=start.y+leave*d.y;
            int band=int(floor(y0/32.));
            if(band<0 || band>=3 || any(lessThan(c,ivec2(0))) || any(greaterThanEqual(c,ivec2(192)))) break;
            float a=y0-float(band*32),b=y1-float(band*32);
            bool blocked=false;
            float inLeaves=canopyColumnLeaves(c,band,a,min(b,32.),blocked);
            if(b>32. && band<2 && !blocked) inLeaves+=canopyColumnLeaves(c,band+1,0.,b-32.,blocked);
            if(blocked) return 0.;
            leafLength+=inLeaves/d.y;
        }
        if(leave>=11.998) break;
        bvec2 crossEdge=lessThanEqual(edge,vec2(leave+.00001));
        c+=ivec2(crossEdge)*stepCell;
        edge+=vec2(crossEdge)*stride;
        t=leave;
    }
    return exp(-1.45*leafLength);
}
vec3 canopyDistantAccess(vec3 relative,vec3 normal) {
    vec3 p=canopyColumnPosition(relative);
    vec3 rounded=round(p);
    p=mix(p,rounded,lessThan(abs(rounded-p),vec3(.002)));
    // Fade only where the 12 m gathering path approaches the outer capture
    // boundary. A garden a few blocks from the player stays fully represented.
    vec3 d=abs(relative);
    float range=(1.-smoothstep(60.,78.,max(d.x,d.z)))*(1.-smoothstep(20.,30.,d.y));
    if(range<=0. || normal.y<-.999 || textureSize(aqualumenRawIndex,0)!=ivec2(128,1801))
        return vec3(1);
    vec3 incoming=vec3(0),open=vec3(0);
    for(int j=0;j<16;j++) {
        int ring=j/4,i=8*ring+2*(j%4)+(ring&1);
        vec3 dir=canopyDirection(i);
        float weight=max(dot(normal,dir),0.);
        vec3 upper=weight*texelFetch(colortex11,ivec2(6+i,0),0).rgb;
        vec3 lower=max(dot(normal,vec3(dir.x,-dir.y,dir.z)),0.)*texelFetch(colortex11,ivec2(6+i,1),0).rgb;
        float pass=weight>0.?canopyColumnRay(p,dir):1.;
        open+=upper+lower;
        incoming+=upper*pass+lower;
    }
    return mix(vec3(1),(incoming+1e-7)/(open+1e-7),range);
}
