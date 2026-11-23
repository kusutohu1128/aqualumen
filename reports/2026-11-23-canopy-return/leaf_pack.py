"""Add single leaf scattering to the established lamp-return paths in preview 10."""
from pathlib import Path
HERE=Path(__file__).resolve().parent

def replace(source,old,new):
    assert source.count(old)==1,old[:60]
    return source.replace(old,new)

def change(name,data):
    if not name.startswith("shaders/"):return data
    if name=="shaders/lib/shadow_vsh.glsl":
        data=replace(data,b"#if defined LOCAL_SOLID || defined LOCAL_GLASS\n    captureBounceFace",b"#if defined LOCAL_SOLID || defined LOCAL_CUTOUT || defined LOCAL_GLASS\n    captureBounceFace")
    elif name=="shaders/lib/bounce_capture.glsl":
        data=replace(data,b"#ifdef LOCAL_SOLID",b"#if defined LOCAL_SOLID || defined LOCAL_CUTOUT")
        tag=(HERE/"leaf_capture.glsl").read_bytes()
        data=replace(data,b"    if((id>=10500",tag+b"\n    if((id>=10500")
    elif name=="shaders/shadowcomp2.csh":
        data=replace(data,b"    if(lit) {", (HERE/"leaf_exit.glsl").read_bytes()+b"\n    if(lit) {")
    elif name=="shaders/shadowcomp3.csh":
        data=replace(data,b'#include "/lib/trace_diffuse_face.glsl"',b'#define LAMP_LEAF_RETURN\n#include "/lib/trace_diffuse_face.glsl"')
    elif name=="shaders/lib/trace_diffuse_face.glsl":
        data=replace(data,b"    vec3 transmission;\n};",b"    vec3 transmission;\n#ifdef LAMP_LEAF_RETURN\n    vec3 leafRadiance;\n#endif\n};")
        old=b"    DiffuseHit hit=DiffuseHit(ivec3(-1),-1,vec2(0),0.,vec3(0));"
        data=replace(data,old,b"#ifdef LAMP_LEAF_RETURN\n    DiffuseHit hit=DiffuseHit(ivec3(-1),-1,vec2(0),0.,vec3(0),vec3(0));\n#else\n"+old+b"\n#endif")
        old=b"if(shape==2 && !towardSun) through*=exp(-1.45*(end-t));"
        data=replace(data,old,(HERE/"leaf_segment.glsl").read_bytes().strip())
        data=replace(data,b"    if(hit.face<0) return vec4(0);",b"""    vec4 leaf=vec4(0);
#ifdef LAMP_LEAF_RETURN
    leaf.rgb=hit.leafRadiance;
#endif
    if(hit.face<0) return leaf;""")
        data=replace(data,b"return vec4(hit.transmission*surface.rgb,surface.a)*fade;",b"return leaf+vec4(hit.transmission*surface.rgb,surface.a)*fade;")
    return data
