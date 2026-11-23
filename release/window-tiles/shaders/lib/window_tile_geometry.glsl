#include "/lib/window_route_address.glsl"
#include "/lib/window_tiles.glsl"
layout(triangles,invocations=16) in;
layout(triangle_strip,max_vertices=36) out;
uniform sampler2D aqualumenLightField;
uniform float viewWidth,viewHeight;
in vec2 vertexUV[];
out vec2 texcoord;
void corner(ivec2 p,ivec2 size) {
    texcoord=vec2(p)/vec2(size);
    gl_Position=vec4(texcoord*2.-1.,0.,1.);
    EmitVertex();
}
void main() {
    if(texelFetch(aqualumenLightField,windowRouteAddress,0).r<.5) {
#ifndef WINDOW_ROUTE
        if(gl_InvocationID==0) {
            for(int k=0;k<3;k++){gl_Position=gl_in[k].gl_Position;texcoord=vertexUV[k];EmitVertex();}
            EndPrimitive();
        }
#endif
        return;
    }
    // One of Iris's two fullscreen triangles supplies the tiled draw.
    if(gl_PrimitiveIDIn!=0) return;
    ivec2 size=ivec2(viewWidth,viewHeight);
    for(int y=0;y<windowTileCount.y;++y) {
        ivec2 tile=ivec2(gl_InvocationID,y);
        bool useWindow=texelFetch(aqualumenLightField,windowTileAddress(tile),0).r>.5;
#ifdef WINDOW_ROUTE
        if(!useWindow) continue;
#else
        if(useWindow) continue;
#endif
        ivec2 a=size*tile/windowTileCount,b=size*(tile+1)/windowTileCount;
        corner(a,size);corner(ivec2(b.x,a.y),size);corner(ivec2(a.x,b.y),size);corner(b,size);
        EndPrimitive();
    }
}
