#ifndef AQUALUMEN_BATHYMETRY
#define AQUALUMEN_BATHYMETRY
// Read-only, world-anchored water columns supplied by the optional client Mod.
// RGBA = undisplaced surface-to-solid-floor depth, camera-relative surface Y,
// validity, reserved. Unknown columns are NOT inferred from the view depth.
uniform sampler2D aqualumenBathymetry;
uniform vec4 aqualumenBathymetryGrid; // camera-relative X/Z origin, span, reference Y
uniform int aqualumenBathymetryReady;
bool localWaterColumn(vec2 position, float meanSurfaceY, out vec3 column) {
    column=vec3(0.0); // depth, world dDepth/dX, world dDepth/dZ
    if (aqualumenBathymetryReady!=1 || aqualumenBathymetryGrid.z<=0.0
        || any(isnan(aqualumenBathymetryGrid)) || any(isinf(aqualumenBathymetryGrid))
        || any(isnan(position)) || any(isinf(position))
        || isnan(meanSurfaceY) || isinf(meanSurfaceY)) return false;
    vec2 coordinate=(position-aqualumenBathymetryGrid.xy)/aqualumenBathymetryGrid.z;
    if (any(lessThan(coordinate,vec2(0.0))) || any(greaterThanEqual(coordinate,vec2(1.0)))) return false;
    ivec2 size=textureSize(aqualumenBathymetry,0);
    if (any(lessThan(size,ivec2(1)))) return false;
    vec2 texel=coordinate*vec2(size)-0.5;
    ivec2 base=ivec2(floor(texel));
    vec2 f=fract(texel);
    vec4 a=texelFetch(aqualumenBathymetry,clamp(base,ivec2(0),size-1),0);
    vec4 b=texelFetch(aqualumenBathymetry,clamp(base+ivec2(1,0),ivec2(0),size-1),0);
    vec4 c=texelFetch(aqualumenBathymetry,clamp(base+ivec2(0,1),ivec2(0),size-1),0);
    vec4 d=texelFetch(aqualumenBathymetry,clamp(base+ivec2(1),ivec2(0),size-1),0);
    // Do not interpolate validity across a dry cell, unknown chunk or a stacked
    // pool. Both stages check the actual undisplaced surface, not wave height.
    vec4 depths=vec4(a.x,b.x,c.x,d.x),surfaces=vec4(a.y,b.y,c.y,d.y);
    vec4 valid=vec4(a.z,b.z,c.z,d.z);
    if (any(isnan(depths)) || any(isinf(depths)) || any(isnan(surfaces)) || any(isinf(surfaces))
        || any(isnan(valid)) || any(isinf(valid))
        || any(lessThanEqual(depths,vec4(0.0))) || any(greaterThan(depths,vec4(128.0)))
        || any(lessThan(valid,vec4(0.5)))
        || any(greaterThan(abs(surfaces-meanSurfaceY),vec4(0.12)))) return false;
    column.x=mix(mix(a.x,b.x,f.x),mix(c.x,d.x,f.x),f.y);
    vec2 cell=aqualumenBathymetryGrid.z/vec2(size);
    column.y=mix(b.x-a.x,d.x-c.x,f.y)/cell.x;
    column.z=mix(c.x-a.x,d.x-b.x,f.x)/cell.y;
    return true;
}
#endif
