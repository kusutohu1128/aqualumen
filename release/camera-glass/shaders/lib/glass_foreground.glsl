// Translucent draws come after the opaque scene has received its view-leg
// transmission. Each foreground fragment contributes at its own depth.
#define main shadeForeground
#include "/lib/terrain.fsh.glsl"
#undef main
void main() {
    shadeForeground();
    gl_FragData[0].rgb*=paneToEye(worldPosition);
}
