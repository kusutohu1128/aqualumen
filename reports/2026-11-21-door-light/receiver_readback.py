"""Add two diagnostic MRT outputs without replacing any production attachment or normal display row."""
import sys
from zipfile import ZipFile

with ZipFile(sys.argv[1]) as src, ZipFile(sys.argv[2], "x") as out:
    for entry in src.infolist():
        code = src.read(entry)
        if entry.filename == "shaders/lib/terrain.fsh.glsl":
            assert code.count(b"RENDERTARGETS:0,5,9,14")==1
            code=code.replace(b"RENDERTARGETS:0,5,9,14",b"RENDERTARGETS:0,5,9,14,2,3")
            pos=code.rindex(b"}")
            code=code[:pos]+b"""
    vec3 L=vec3(.2126,.7152,.0722);
    float skyAccess=smoothstep(0.0,1.0,lightmap.y)*vertexColor.a;
    gl_FragData[4]=vec4(lightmap,vertexColor.a,dot(albedo,L));
    gl_FragData[5]=vec4(dot(color,L),dot(albedo*diffuseFace(normal,0)*skyAccess,L),
                        dot(sunRadiance,L),dot(localRadiance,L));
"""+code[pos:]
        elif entry.filename=="shaders/prepare.fsh":
            code=code.replace(b"const int colortex0Format",b"const int colortex2Format = RGBA16F;\nconst int colortex3Format = RGBA16F;\nconst int colortex0Format",1)
        elif entry.filename=="shaders/final.fsh":
            code=code.replace(b"void main()",b"void renderProduction()")
            code+=b"""
uniform sampler2D colortex2;
uniform sampler2D colortex3;
uniform sampler2D colortex4;
void main() {
    renderProduction();
    ivec2 p=ivec2(gl_FragCoord.xy); int row=p.y%5;
    vec3 L=vec3(.2126,.7152,.0722);
    vec4 mesh=texelFetch(colortex2,p,0), terms=texelFetch(colortex3,p,0);
    if(row==1) gl_FragColor=vec4(mesh.rgb,1);
    if(row==2) gl_FragColor=vec4(sqrt(max(vec3(terms.x,dot(texelFetch(colortex4,p,0).rgb,L),
                                              dot(texelFetch(colortex0,p,0).rgb,L)),vec3(0))),1);
    if(row==3) gl_FragColor=vec4(sqrt(max(terms.yzw,vec3(0))),1);
    if(row==4) gl_FragColor=vec4(sqrt(max(mesh.a,0.0)),exposureScale()/4.0,
                                 float(texelFetch(colortex10,p,0).a>0.5),1);
}
"""
        out.writestr(entry,code)
