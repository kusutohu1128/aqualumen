"""On one fragment, measure both G-buffer encodings against forward lighting."""
from zipfile import ZipFile
from packing import HERE, PACK, WORK, build, corrected, render
from meter import code, replace
import sys

DIAG = WORK / "Aqualumen-Coating-Comparison.zip"
with ZipFile(PACK) as normal:
    final = normal.read("shaders/final.fsh").decode()
display = final[final.index("float exposureScale()"):final.index("void main()")]
display += """
vec3 displayCodes(vec3 hdr,float exposure) {
    return floor(255.*pow(tone(hdr,exposure),vec3(1./2.2))+.5);
}
float peakChannel(vec3 rgb) { return max(rgb.r,max(rgb.g,rgb.b)); }
"""


def diagnostic(name, shader):
    shader = corrected(name, shader)
    path = name.removeprefix("shaders/")
    if path == "final.fsh":
        return replace(shader, "void main() {", (HERE/"compare.glsl").read_text()+
                       "\nvoid main() {\n    if(readComparison()) return;")
    shader = code(path, shader)
    if path != "deferred.fsh":
        return shader
    shader = replace(shader, "void main() {", '#include "/lib/display_exposure.glsl"\nuniform sampler2D aqualumenLampExposure;\n'+
                     display+"\nvoid main() {")
    shader = replace(shader, "vec3 measuredLocal=vec3(0.);",
                     "vec3 measuredLocal=vec3(0.), previousLocal=vec3(0.);")
    shader = replace(shader, "        measuredLocal=local;", """        previousLocal=local;
        if(stored.z<0.) {
            // Recreate the exact two 12-bit fields of the original format.
            vec2 previous=areaUnpackPair(areaPackPair(coating));
            vec3 otherView=previous.x>0.?normalize(relativeWorld(vec3(0))-position):vec3(0.);
            vec3 oldSpecular,oldThrough;
            vec3 oldDiffuse=lampLighting(position,n,otherView,previous.y,blueLevel.y,false,bounce.a,
                                         previous.x>0.,leaf,oldSpecular,oldThrough);
            previousLocal=albedo*(oldDiffuse+bounce.rgb)+previous.x*oldSpecular;
            if(leaf.valid) previousLocal+=leafTransmittance(albedo)*oldThrough;
        }
        measuredLocal=local;""")
    shader = replace(shader, "gl_FragData[5]=vec4(peak,bright,float(bits),1.);", """
    // Apply the ordinary display shoulder and gamma at the same live exposure
    // to three versions of this opaque surface before atmosphere, rain and AA.
    vec3 base=color-measuredLocal;
    float exposure=exposureScale();
    vec3 reference=displayCodes(base+oracle.rgb,exposure);
    float oldStep=peakChannel(abs(reference-displayCodes(base+previousLocal,exposure)));
    float stepNow=peakChannel(abs(reference-displayCodes(color,exposure)));
    if(any(isnan(previousLocal)) || any(isinf(previousLocal))) bits=bits|128;
    gl_FragData[5]=vec4(peakChannel(abs(oracle.rgb-previousLocal)),peak,oldStep+256.*stepNow,float(bits));""")
    return shader


if __name__ == "__main__":
    digest=build(DIAG, diagnostic)
    print(digest, flush=True)
    if len(sys.argv)>1:
        render(DIAG, digest, sys.argv[1])
