// Default Minecraft cube-face UVs on an exposed foliage boundary.
float leafSurfaceCoverage(int slot,vec3 point) {
    vec3 f=clamp(point,0.0,1.0);
    vec3 edge=min(f,1.0-f);
    vec2 uv;
    if(edge.x<=edge.y && edge.x<=edge.z) uv=vec2(f.x<.5?f.z:1.0-f.z,1.0-f.y);
    else if(edge.y<=edge.z) uv=vec2(f.x,f.y<.5?1.0-f.z:f.z);
    else uv=vec2(f.z<.5?1.0-f.x:f.x,1.0-f.y);
    vec2 st=clamp(uv*16.0-.5,vec2(0),vec2(15));
    ivec2 a=ivec2(st),b=min(a+1,ivec2(15));
    vec2 t=fract(st);
    uint top=texelFetch(aqualumenDoorMask,ivec2(a.y,39+2*slot),0).r;
    uint bottom=texelFetch(aqualumenDoorMask,ivec2(b.y,39+2*slot),0).r;
    return mix(mix(float((top>>a.x)&1u),float((top>>b.x)&1u),t.x),
               mix(float((bottom>>a.x)&1u),float((bottom>>b.x)&1u),t.x),t.y);
}

vec3 foliageSheet(int word,int slot) {
    uint spriteBits=texelFetch(aqualumenDoorMask,ivec2(1,38+2*slot),0).r;
    // Composite and hand receivers also use this path under GLSL 3.30.
    vec4 sprite=vec4(spriteBits&255u,(spriteBits>>8u)&255u,(spriteBits>>16u)&255u,spriteBits>>24u)/255.0;
    vec3 tint=vec3((word>>12)&15,(word>>16)&15,(word>>20)&15)/15.0;
    vec3 pigment=pow(max(sprite.rgb*tint,vec3(0.0)),vec3(2.2));
    float peak=max(pigment.r,max(pigment.g,pigment.b));
    vec3 hue=mix(vec3(1),pigment/max(peak,1e-5),.50);
    hue/=dot(hue,vec3(.2126,.7152,.0722));
    // Two cutout sheets and a sparse interior average to the same one-metre
    // transmission as the receiver's canopy model, for uncorrelated texels.
    // A very sparse sprite still lets its genuine openings pass light.
    const float meanSurface=.5091564; // exp(-0.5*(1.45-interior))
    float meanSheet=clamp((meanSurface-(1.0-sprite.a))/max(sprite.a,1e-5),0.0,.95);
    return clamp(meanSheet*hue,vec3(.025),vec3(.95));
}
vec3 leafSheetPath(int slot,vec3 sheet,vec3 entry,vec3 exit,float distanceInside,bool entryFace,bool exitFace) {
    const float interior=.10;
    float a=entryFace?leafSurfaceCoverage(slot,entry):0.0;
    float b=exitFace?leafSurfaceCoverage(slot,exit):0.0;
    // Culled internal faces have no sprite to project. Represent their share
    // of extinction by the mean medium, avoiding a seam inside a solid crown.
    float hidden=2.0-float(entryFace)-float(exitFace);
    float medium=exp(-(interior+.5*(1.45-interior)*hidden)*distanceInside);
    vec3 faces=mix(vec3(1),sheet,a)*mix(vec3(1),sheet,b);
    return medium*pow(faces,vec3(min(1.0,8.0*distanceInside)));
}

vec3 foliageSegment(int word,vec3 entry,vec3 exit,float distanceInside,bool entryFace,bool exitFace) {
    int slot=(word>>6)&63;
    if(slot==0) return vec3(exp(-1.45*distanceInside));
    return leafSheetPath(slot,foliageSheet(word,slot),entry,exit,distanceInside,entryFace,exitFace);
}
