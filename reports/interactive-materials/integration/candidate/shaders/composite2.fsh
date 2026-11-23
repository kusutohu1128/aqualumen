#version 330 compatibility
uniform sampler2D colortex12;
in vec2 texcoord;
/* RENDERTARGETS:13 */
void main() {
    ivec2 grid=textureSize(colortex12,0);
    vec2 stepSize=vec2(max(0.68,float(grid.y)/300.0))/vec2(grid);
    // Normalized symmetric Gaussian. The linear sample pairs straddle two texels.
    const float x[5]=float[5](-3.23077,-1.38462,0.0,1.38462,3.23077);
    const float w[5]=float[5](0.07027,0.31622,0.22702,0.31622,0.07027);
    vec3 sum=vec3(0);
    for(int j=0;j<5;j++) for(int i=0;i<5;i++)
        sum+=w[i]*w[j]*texture(colortex12,texcoord+stepSize*vec2(x[i],x[j])).rgb;
    gl_FragData[0]=vec4(sum,1);
}
