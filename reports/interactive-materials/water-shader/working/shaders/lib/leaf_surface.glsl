#ifndef AQUALUMEN_LEAF_SURFACE
#define AQUALUMEN_LEAF_SURFACE
#include "/lib/uniforms.glsl"
#include "/lib/local_light_grid.glsl"
// A leaf block (material 10300) is a one metre proxy of a canopy volume. Only
// its exterior faces are normally drawn, so the visible face carries the whole
// cube: the owning voxel is recovered from the face, never from a neighbour.
// Model: Lambertian two-sided leaf (reflectance rho, transmittance tau) after
// Gates et al. 1965 (Appl. Opt. 4:11) and Verhoef 1984 (SAIL); beam
// attenuation in the proxy volume follows Monsi & Saeki 1953 (Beer-Lambert).
const int LEAF_MATERIAL=10300;
// 1/m. Identical to the constant of the lamp path through a leaf cell.
const float LEAF_EXTINCTION=1.45;
struct LeafSurface {
    bool valid;
    ivec3 cell;    // light-grid cell of the owning voxel
    vec3 centre;   // camera-relative centre of the owning voxel
    vec3 normal;   // axis-snapped outward normal of the visible face
};
LeafSurface leafSurfaceNone() { return LeafSurface(false,ivec3(0),vec3(0),vec3(0)); }
// Faces lie on integer planes, so the normal axis has a half-metre margin and a
// face on a cell boundary still names its own cube. Tangential coordinates lie
// strictly inside the face. The lattice is aligned with world integers because
// the grid origin moves in whole eight-metre steps; membership in the 64 cell
// grid is not required for the far-field estimate.
LeafSurface leafSurface(int material,vec3 position,vec3 normal) {
    LeafSurface leaf=leafSurfaceNone();
    if(material!=LEAF_MATERIAL) return leaf;
    vec3 a=abs(normal);
    int axis=a.x>a.y && a.x>a.z?0:(a.y>a.z?1:2);
    if(!(a[axis]>0.99)) return leaf;
    vec3 n=vec3(0.0);
    n[axis]=normal[axis]>0.0?1.0:-1.0;
    vec3 shift=mod(cameraPosition,8.0)+32.0;
    vec3 g=position+shift;
    vec3 c=floor(g);
    c[axis]=floor(g[axis]-0.5*n[axis]);
    if(any(isnan(c)) || any(isinf(c)) || any(greaterThan(abs(c),vec3(1.0e6)))) return leaf;
    leaf.valid=true;
    leaf.cell=ivec3(c);
    leaf.centre=c+0.5-shift;
    leaf.normal=n;
    return leaf;
}
#endif
