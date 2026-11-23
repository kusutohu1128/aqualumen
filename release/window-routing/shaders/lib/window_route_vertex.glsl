#include "/lib/window_route_address.glsl"
uniform sampler2D aqualumenLightField;
out vec2 texcoord;
void main() {
    texcoord=gl_MultiTexCoord0.xy;
    bool pane=texelFetch(aqualumenLightField,windowRouteAddress,0).r>0.5;
#ifdef WINDOW_ROUTE
    bool draw=pane;
#else
    bool draw=!pane;
#endif
    gl_Position=draw ? ftransform() : vec4(0.,0.,2.,1.);
}
