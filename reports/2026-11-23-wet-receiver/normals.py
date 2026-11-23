"""Audit the raw, triangle, and decoded receiver normals on surveyed flat stone."""
from packing import WORK, build, corrected, replace
from room import HERE, STAGES, COMPILER, CACHE, WetRoom, guarded
from meter import code

PACK=WORK/"Aqualumen-Receiver-Normals.zip"


def audit(name, shader):
    path=name.removeprefix("shaders/")
    shader=corrected(name,shader)
    if path=="lib/terrain.fsh.glsl":
        shader=replace(shader,"void main() {","""#ifdef AQUALUMEN_FORWARD_FIELD
vec4 surveyRaw=vec4(0.);
vec4 surveyTriangle=vec4(0.);
#endif
void main() {""")
        shader=replace(shader,"    vec4 atlas=", """#ifdef AQUALUMEN_FORWARD_FIELD
    vec3 triangle=cross(dFdx(worldPosition),dFdy(worldPosition));
    triangle=normalize(triangle)*(triangle.y<0.?-1.:1.);
#endif
    vec4 atlas=""")
        return replace(shader,"    if(pendingAreaLight) {","""    if(pendingAreaLight) {
        surveyRaw=vec4(normal,float(film>0.));
        surveyTriangle=vec4(triangle,float(abs((worldPosition.y+cameraPosition.y)-151.)<.002));""")
    if path=="gbuffers_terrain.fsh":
        shader=replace(shader,"/* RENDERTARGETS:0,5,9,14,15 */","/* RENDERTARGETS:0,5,9,14,15,1,3 */")
        return replace(shader,'#include "/lib/terrain.fsh.glsl"','''#define main surveyTerrain
#include "/lib/terrain.fsh.glsl"
#undef main
void main() {
    surveyTerrain();
    gl_FragData[5]=surveyRaw;
    gl_FragData[6]=surveyTriangle;
}
''')
    if path=="prepare.fsh":
        shader=code(path,shader)
        return replace(shader,"const int colortex2Format", "const int colortex3Format = RGBA32F;\nconst int colortex2Format")
    if path=="deferred.fsh":
        shader=replace(shader,"/* RENDERTARGETS:0,4,8,10,14 */","uniform sampler2D colortex1;\nuniform sampler2D colortex3;\n/* RENDERTARGETS:0,4,8,10,14,2 */")
        shader=replace(shader,"    if(depth<.999999 && directSun.a<-.5)", "    gl_FragData[5]=vec4(0.);\n    if(depth<.999999 && directSun.a<-.5)")
        return replace(shader,"        vec3 position=relativeWorld", """        vec4 raw=texelFetch(colortex1,pixel,0),triangle=texelFetch(colortex3,pixel,0);
        if(raw.a>.5 && triangle.a>.5 && raw.y>.95 && triangle.y>.95) {
            float tag=stored.z<0.?7.:(stored.w<0.?-stored.w:0.);
            // Encode the horizontal components of all three near-vertical normals
            // at 1/32768 resolution. Clamp off-scale observations explicitly.
            vec2 xz0=raw.xz,xz1=n.xz,xz2=triangle.xz;
            bool overflow=any(greaterThan(max(abs(xz0),max(abs(xz1),abs(xz2))),vec2(.06245)));
            vec2 bias=vec2(2048.);
            vec2 a=clamp(round(xz0*32768.)+bias,0.,4095.);
            vec2 b=clamp(round(xz1*32768.)+bias,0.,4095.);
            vec2 c=clamp(round(xz2*32768.)+bias,0.,4095.);
            gl_FragData[5]=vec4(a.x+4096.*a.y,b.x+4096.*b.y,c.x+4096.*c.y,8.+tag+16.*float(overflow));
        }
        vec3 position=relativeWorld""")
    if path=="final.fsh":
        first=shader.split("void main() {")[0]
        return first+"""uniform sampler2D colortex2;
void main() {
    ivec2 sz=textureSize(colortex2,0),top=ivec2(int(gl_FragCoord.x),sz.y-1-int(gl_FragCoord.y));
    if(top.y==2 && top.x>=8 && top.x<264) {
        float t=float(top.x-8);
        gl_FragColor=vec4(vec3(t,255.-t,173.)/255.,1.);
        return;
    }
    ivec2 panel=top/(sz/2),src=2*(top-panel*(sz/2))+1;
    vec4 obs=texelFetch(colortex2,ivec2(src.x,sz.y-1-src.y),0);
    int k=panel.x+2*panel.y;
    float v=obs[k];
    gl_FragColor=vec4(vec3(mod(v,256.),mod(floor(v/256.),256.),floor(v/65536.))/255.,1.);
}
"""
    return shader


class CameraRoom(WetRoom):
    def geometry(self,names):
        return dict(**super().geometry(names),middleCamera=[409.48,151,-405.95,143.8,18.])
    def datapack(self,names):
        files=super().datapack(names)
        directory="data/animal/function/"
        k=directory+"s1.mcfunction"
        files[k]=replace(files[k],"409.48 151 -405.95 153.8 7","409.48 151 -405.95 143.8 18")
        for step in ("v1","e1"):
            k=directory+step+".mcfunction"
            files[k]=replace(files[k],"x_rotation=6.95..7.05,y_rotation=153.75..153.85",
                             "x_rotation=17.95..18.05,y_rotation=143.75..143.85")
        return files


if __name__=="__main__":
    digest=build(PACK,audit)
    print(digest,flush=True)
    fixed=dict(backend="vgl",size="1600x900",settle="1",glcache=str(CACHE),
               stages=",".join(STAGES),**{"period-ticks":"260","shot-gap":"0.15","compiler-mod":str(COMPILER)})
    guarded.launch(PACK,"normals-at-two-angles","off",fixed,HERE,CameraRoom)
