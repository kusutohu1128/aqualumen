"""Read the normal final output, opaque snapshot, post-composite light, and display exposure together."""
import sys
from zipfile import ZipFile

with ZipFile(sys.argv[1]) as src, ZipFile(sys.argv[2],"x") as out:
    for entry in src.infolist():
        code=src.read(entry)
        if entry.filename=="shaders/final.fsh":
            assert code.count(b"void main()")==1
            code=code.replace(b"void main()", b"void renderOriginal()")
            code+=b"""
uniform sampler2D colortex4;
uniform sampler2D colortex14;
void main() {
    renderOriginal();
    ivec2 p=ivec2(gl_FragCoord.xy);
    int row=p.y%4;
    vec3 luma=vec3(.2126,.7152,.0722);
    if(row==1) {
        vec3 opaque=texelFetch(colortex4,p,0).rgb;
        vec3 scene=texelFetch(colortex0,p,0).rgb;
        float local=texelFetch(colortex14,p,0).r;
        gl_FragColor=vec4(sqrt(max(vec3(dot(opaque,luma),dot(scene,luma),local),vec3(0))),1);
    } else if(row==2) {
        float front=texelFetch(depthtex0,p,0).r;
        float back=texelFetch(depthtex1,p,0).r;
        float material=texelFetch(colortex10,p,0).a;
        gl_FragColor=vec4(exposureScale()/4.0,float(front!=back),float(material<0),1);
    } else if(row==3) {
        gl_FragColor=vec4(sqrt(max(texelFetch(colortex0,p,0).rgb,vec3(0))),1);
    }
}
"""
        out.writestr(entry,code)
