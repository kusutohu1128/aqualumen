#version 430 compatibility
// Same vertex outputs as the fallback shadow program; the geometry stage
// forwards them unchanged and captures each triangle for local lights.
#include "/lib/shadow_vsh.glsl"
