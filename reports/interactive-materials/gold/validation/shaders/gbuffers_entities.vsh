#version 430 compatibility
#include "/lib/settings.glsl"
#include "/lib/uniforms.glsl"
#include "/lib/animal_sky.glsl"
#include "/lib/animal_ground.glsl"

uniform int entityId;
out vec3 animalSkyAccess;
out vec4 animalReturn;
#define main meshVertex
#include "/lib/terrain.vsh.glsl"
#undef main

void main() {
    meshVertex();
    animalSkyAccess=vec3(1);
    animalReturn=vec4(0);
    if(entityId==entityCasterId || entityId==entitySelfId) {
        animalSkyAccess=animalSky(worldPosition,worldNormal);
        animalReturn=animalGround(worldPosition,worldNormal);
    }
}
