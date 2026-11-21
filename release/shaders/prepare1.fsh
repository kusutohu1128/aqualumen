#version 330 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/atmosphere.glsl"
#include "/lib/water.glsl"
#include "/lib/clouds.glsl"
uniform sampler2D colortex7;
uniform sampler2D colortex6;
/* RENDERTARGETS:11 */
/* const int colortex11Format = RGBA16F; */
void main() {
    ivec2 cell=ivec2(gl_FragCoord.xy);
    if(cell.y>=10) {
        vec2 local=(vec2(cell.x,cell.y-10)-31.5)*8.0-mod(cameraPosition.xz,8.0);
        vec3 sun=sunDirection();
        // Same cloud column as the visible sky, sampled on a world-anchored
        // horizontal plane covering the surroundings of the player.
        vec3 clear=cachedSolarTransmission(colortex7);
        float cloud=1.0;
        if(earthAtmosphere() && sun.y>0.0 && max(clear.r,max(clear.g,clear.b))>0.0001)
            cloud=cloudSolarAt(sun,max(cameraPosition.y-63.0,2.0),local);
        gl_FragData[0]=vec4(clear*cloud,cloud);return;
    }
    if(cell.x>=6) {gl_FragData[0]=vec4(0.0);return;}
    vec3 normal=vec3(0.0);
    normal[cell.x/2]=(cell.x%2==1)?1.0:-1.0;
    int row=cell.y;
    float depth=row<2?0.0:0.5*exp2(float(row-2));
    vec3 sum=vec3(0.0);
    // Equal-solid-angle Fibonacci directions. The dry hemisphere below the
    // horizon samples the sky LUT's diffuse ground environment.
    const int count=384;
    for(int i=0;i<count;++i) {
        float u=(float(i)+0.5)/float(count);
        float mu=row==0?2.0*u-1.0:u;
        float azimuth=float(i)*2.39996323;
        float radial=sqrt(max(1.0-mu*mu,0.0));
        vec3 air=vec3(radial*cos(azimuth),mu,radial*sin(azimuth));
        vec3 dir=air;
        vec3 throughput=vec3(1.0);
        if(row!=0) {
            dir=-refract(-air,vec3(0.0,1.0,0.0),1.0/1.333);
            // Etendue maps air solid angle into water. The n^2 in radiance
            // cancels the inverse n^2 in that solid angle.
            throughput=(1.0-waterFresnel(mu,1.0,1.333))*mu/dir.y*waterTransmission(depth/dir.y);
        }
        float cosine=dot(normal,dir);
        if(cosine>0.0) sum+=sampleSky(colortex6,air)*throughput*cosine;
    }
    gl_FragData[0]=vec4(sum*(row==0?4.0:2.0)/float(count),1.0);
}
