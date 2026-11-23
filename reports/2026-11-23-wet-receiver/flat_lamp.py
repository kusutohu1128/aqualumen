"""Measure how using the surveyed stone floor's true normal changes local lighting."""
from normals import CameraRoom
from packing import WORK, build, replace
from paired import display
from room import HERE, STAGES, COMPILER, CACHE, guarded

PACK=WORK/"Aqualumen-Flat-Stone-Lamp-Comparison-r2.zip"


def compare(name, shader):
    if name=="shaders/prepare.fsh":
        return replace(shader,"const int colortex0Format","const int colortex2Format = RGBA32F;\nconst int colortex0Format")
    if name=="shaders/final.fsh":
        prefix=shader.split("void main() {")[0]
        return prefix+"""uniform sampler2D colortex2;
void main() {
    ivec2 p=ivec2(gl_FragCoord.xy), size=textureSize(colortex2,0);
    if(p.y==size.y-3 && p.x>=8 && p.x<264) {
        float t=float(p.x-8);
        gl_FragColor=vec4(vec3(t,255.-t,173.)/255.,1.);
        return;
    }
    gl_FragColor=vec4(texelFetch(colortex2,p,0).rgb/255.,1.);
}
"""
    if name!="shaders/deferred.fsh":
        return shader
    shader=replace(shader,"/* RENDERTARGETS:0,4,8,10,14 */","/* RENDERTARGETS:0,4,8,10,14,2 */")
    shader=replace(shader,"void main() {",'#include "/lib/display_exposure.glsl"\nuniform sampler2D aqualumenLampExposure;\n'+display+
                   "\nvoid main() {\n    gl_FragData[5]=vec4(0.);")
    return replace(shader,"        color+=local;","""        vec3 point=cameraPosition+position;
        // Only the interior of the 6 x 7 surveyed cobblestone floor. Leave
        // adjacent geometry, the stone edges, and the cow out of the statistic.
        if(coating.x>0. && !leaf.valid && n.y>.99 && abs(point.y-151.)<.004 &&
           point.x>404.005 && point.x<409.995 && point.z> -411.995 && point.z< -405.005) {
            vec3 up=vec3(0.,1.,0.);
            vec4 flatBounce=bounceAtReceiver(position,up);
            vec3 flatSpecular,flatThrough;
            vec3 flatDiffuse=lampLighting(position,up,view,coating.y,blueLevel.y,false,
                                          flatBounce.a,true,leaf,flatSpecular,flatThrough);
            vec3 flatLocal=albedo*(flatDiffuse+flatBounce.rgb)+coating.x*flatSpecular;
            float exposure=exposureScale();
            vec3 baseline=displayCodes(color+local,exposure);
            vec3 flatDisplay=displayCodes(color+flatLocal,exposure);
            vec3 specOnly=displayCodes(color+local+coating.x*(flatSpecular-specular),exposure);
            bool finiteValues=!any(isnan(flatLocal)) && !any(isinf(flatLocal)) &&
                              !any(isnan(local)) && !any(isinf(local));
            gl_FragData[5]=vec4(peakChannel(abs(flatDisplay-baseline)),peakChannel(abs(specOnly-baseline)),
                                finiteValues?187.:252.,1.);
        }
        color+=local;""")


if __name__=="__main__":
    digest=build(PACK,compare)
    print(digest,flush=True)
    fixed=dict(backend="vgl",size="1600x900",settle="1",glcache=str(CACHE),stages=",".join(STAGES),
               **{"period-ticks":"260","shot-gap":"0.15","compiler-mod":str(COMPILER)})
    guarded.launch(PACK,"flat-stone-lamp-r2","off",fixed,HERE,CameraRoom)
