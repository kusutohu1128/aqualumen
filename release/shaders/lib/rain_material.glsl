#ifndef AQUALUMEN_RAIN_MATERIAL
#define AQUALUMEN_RAIN_MATERIAL
// Relative pore scattering, saturated perceptual roughness, continuous-film
// coverage. These estimates distinguish broad vanilla material families.
vec3 rainMaterial(int id) {
    if(id==10600) return vec3(.72,.22,.91); // dressed stone and polished tiles
    if(id==10601 || id==10001) return vec3(.55,.34,.78); // stone, earth and masonry
    if(id==10602) return vec3(.58,.38,.62); // sawn timber
    if(id>=10301 && id<=10303) return vec3(.63,.36,.69); // slab mesh, shared across substrates
    if(id==10003) return vec3(.48,.52,.29); // loose grains retain a thinner sheen
    if(id==10002) return vec3(.60,.46,.40); // stratified stone and grass-topped soil
    return vec3(1.0,1.0,0.0);
}
#endif
