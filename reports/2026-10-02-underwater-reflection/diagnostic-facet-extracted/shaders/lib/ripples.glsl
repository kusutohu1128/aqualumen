#ifndef AQUALUMEN_RIPPLES
#define AQUALUMEN_RIPPLES
uniform sampler2D aqualumenRippleA;
uniform vec4 aqualumenGrid;
uniform int aqualumenActive;
// Coordinates follow Iris's shifted cameraPosition; the mod sends camera-relative origins.
vec3 rippleState(vec2 worldXZ) {
    if(aqualumenActive==0) return vec3(0.0);
    vec2 uv=(worldXZ-cameraPosition.xz-aqualumenGrid.xy)/aqualumenGrid.z;
    if(any(lessThan(uv,vec2(0.005))) || any(greaterThan(uv,vec2(0.995)))) return vec3(0.0);
    vec2 cell=vec2(1.0/512.0);
    float height=textureLod(aqualumenRippleA,uv,0.0).r;
    float dx=(textureLod(aqualumenRippleA,uv+vec2(cell.x,0),0).r-textureLod(aqualumenRippleA,uv-vec2(cell.x,0),0).r)/0.25;
    float dz=(textureLod(aqualumenRippleA,uv+vec2(0,cell.y),0).r-textureLod(aqualumenRippleA,uv-vec2(0,cell.y),0).r)/0.25;
    return vec3(clamp(height,-0.07,0.07),clamp(dx,-0.35,0.35),clamp(dz,-0.35,0.35));
}
#endif
