#version 330 compatibility
uniform sampler2D colortex0;
uniform sampler2D colortex10;
uniform sampler2D depthtex0;
uniform sampler2D depthtex1;
in vec2 texcoord;
/* RENDERTARGETS:12 */
void main() {
    ivec2 size=textureSize(colortex0,0);
    // Cover each input pixel in proportion to its area. The rasterized
    // pixel footprint includes the actual rounded viewport on odd resolutions.
    ivec2 outputSize=max(ivec2(1),ivec2(round(1.0/fwidth(texcoord))));
    vec2 scale=vec2(size)/vec2(outputSize);
    vec2 lower=vec2(ivec2(gl_FragCoord.xy))*scale;
    vec2 upper=lower+scale;
    ivec2 first=max(ivec2(floor(lower)),ivec2(0));
    ivec2 last=min(ivec2(ceil(upper)),size);
    vec3 sum=vec3(0);
    for(int y=first.y;y<last.y;y++) for(int x=first.x;x<last.x;x++) {
        ivec2 p=ivec2(x,y);
        vec4 material=texelFetch(colortex10,p,0);
        if(material.a>=0.0) continue;
        float z=texelFetch(depthtex0,p,0).r;
        if(z>=0.999999 || z!=texelFetch(depthtex1,p,0).r) continue;
        vec2 area=min(upper,vec2(p+1))-max(lower,vec2(p));
        sum+=area.x*area.y*min(material.rgb,max(texelFetch(colortex0,p,0).rgb,vec3(0)));
    }
    gl_FragData[0]=vec4(sum/(scale.x*scale.y),1.0);
}
