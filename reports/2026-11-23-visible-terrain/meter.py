"""Compare the original forward local radiance and the reconstructed deferred term on one frame."""
from hashlib import sha256
import re
from zipfile import ZipFile
from visible_pack import HERE, PACK, WORK, STUDY_SHA

METER = WORK / "Aqualumen-Ownership-Meter.zip"
OWNERS = {"terrain":1,"entities":7,"hand":8,"textured_lit":9,"textured":10,"basic":11,"skybasic":12}


def replace(shader, old, new):
    assert shader.count(old)==1,old
    return shader.replace(old,new)


def code(name, shader):
    if name=="lib/local_lighting.glsl":
        shader=replace(shader,"bool pendingAreaLight=false;","bool pendingAreaLight=false, auditRequested=false, auditRemoved=false;\nvec3 auditOriginal=vec3(0.);\nfloat auditClass=1.;")
        # Evaluate the ordinary forward lighting once on the original interpolants.
        return replace(shader,"pendingAreaLight=true;\n        return vec3(0);","pendingAreaLight=true;\n        auditRequested=true;")
    if name=="lib/terrain.fsh.glsl":
        return replace(shader,"    if(pendingAreaLight) {", """    auditOriginal=localRadiance;
    if(auditRequested) auditClass=2.+float(leaf.valid)+2.*float(film>0.);
    else if(pendingAreaLight) auditClass=6.;
    if(pendingAreaLight) {
        auditRemoved=true;""")
    if name.startswith("gbuffers_") and name.endswith(".fsh"):
        program=name[9:-4]
        if program not in OWNERS:
            return shader
        if program=="skybasic":
            shader=replace(shader,"/* DRAWBUFFERS:05 */","/* RENDERTARGETS:0,5 */")
        match=re.search(r"/\* RENDERTARGETS:([0-9,]+) \*/",shader)
        targets=match.group(1)
        shader=replace(shader,match.group(),f"/* RENDERTARGETS:{targets},1 */")
        first,rest=shader.split("\n",1)
        payload="vec4(auditOriginal,auditClass+16.*float(auditRemoved))" if program=="terrain" else f"vec4(0.,0.,0.,{OWNERS[program]}.)"
        return first+"\n#define main auditGeometryMain\n"+rest+f"""
#undef main
void main() {{
    auditGeometryMain();
    gl_FragData[{len(targets.split(','))}]={payload};
}}
"""
    if name=="prepare.fsh":
        return replace(shader,"const int colortex0Format", """const int colortex1Format = RGBA32F;
const vec4 colortex1ClearColor = vec4(0.0, 0.0, 0.0, 0.0);
const int colortex2Format = RGBA32F;
const int colortex0Format""")
    if name=="deferred.fsh":
        shader=replace(shader,"/* RENDERTARGETS:0,4,8,10,14 */","uniform sampler2D colortex1;\n/* RENDERTARGETS:0,4,8,10,14,2 */")
        shader=replace(shader,"    if(depth<.999999 && directSun.a<-.5)","    bool didShade=depth<.999999 && directSun.a<-.5;\n    vec3 measuredLocal=vec3(0.);\n    if(didShade)")
        shader=replace(shader,"        color+=local;","        measuredLocal=local;\n        color+=local;")
        return replace(shader,"    gl_FragData[4]=vec4(lampLuminance);","""    gl_FragData[4]=vec4(lampLuminance);
    vec4 oracle=texelFetch(colortex1,pixel,0);
    // Record what forward actually subtracted independently of the solar-alpha
    // marker and the depth test that caused the deferred addition.
    float rawClass=oracle.a;
    bool valid=abs(rawClass-round(rawClass))<1e-5 && rawClass>=0. && rawClass<=31.;
    vec3 err=abs(oracle.rgb-measuredLocal);
    float peak=max(err.r,max(err.g,err.b));
    float bright=max(oracle.r,max(oracle.g,oracle.b));
    int bits=(valid?int(round(rawClass)):15)+32*int(didShade)+64*int(bright>.01);
    if(any(isnan(err)) || any(isinf(err))) bits+=128;
    gl_FragData[5]=vec4(peak,bright,float(bits),1.);""")
    if name=="final.fsh":
        return replace(shader,"void main() {",(HERE/"readout.glsl").read_text()+"\nvoid main() {\n    if(auditReadout()) return;")
    return shader


def build():
    assert sha256(PACK.read_bytes()).hexdigest()==STUDY_SHA
    with ZipFile(PACK) as src, ZipFile(METER,"w") as dst:
        for entry in src.infolist():
            data=src.read(entry)
            if entry.filename.startswith("shaders/") and entry.filename.endswith((".fsh",".glsl")):
                data=code(entry.filename[8:],data.decode()).encode()
            dst.writestr(entry,data)
    return METER


if __name__=="__main__":
    print(sha256(build().read_bytes()).hexdigest())
