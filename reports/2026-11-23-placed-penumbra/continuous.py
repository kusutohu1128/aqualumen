"""Keep each compact source index tied to its tile and join partial shadow estimates."""
from pack import HERE, WORK, NAME, build, replace
from meter import audit

NORMAL=NAME.replace("-Study","-Continuous")
METER=NAME.replace("-Study","-Continuous-Meter")

def transform(name,s,diagnostic):
    if diagnostic:
        s=audit(name,s)
    if name=="shaders/lib/local_lighting.glsl":
        s=replace(s,"int openReceiverRow,openSourceSlot;","int openReceiverRow,openSourceSlot,openSourceRecord;\nvec3 openSurfaceNormal;")
        start=s.index("float cachedBoxVisibility(")
        end=s.index("#endif",start)
        s=s[:start]+(HERE/"continuous.glsl").read_text()+s[end:]
        s=replace(s,"openReceiverRow=row;openSourceSlot=i;","openReceiverRow=row;openSourceSlot=i;openSourceRecord=record;openSurfaceNormal=normal;")
        start=s.index("        ivec3 cell;\n        int flags=torchCellFlags(")
        end=s.index("\n    }\n#endif",start)
        branch="""
        ivec3 cell=ivec3(floor(start));
        int slot;
        int flags=flagsForTorch(cell,centre,slot);
        if(flags!=0) {
            if((flags&(1<<slot))!=0 && all(greaterThanEqual(min(fract(start),1.-fract(start)),vec3(.0001)))) {
                SET_CLEAR
                return vec3(1);
            }
            if((flags&(1<<(slot+12)))!=0) {
                SET_ANALYTIC
                return vec3(continuousBox(cell,slot,start,centre,u,v,radius));
            }
        }"""
        branch=branch.replace("SET_CLEAR","probeMethod=1;" if diagnostic else "").replace("SET_ANALYTIC","probeMethod=2;" if diagnostic else "")
        if diagnostic:
            branch="""
        if(probeBaseline) {
            ivec3 cell;
            if((torchCellFlags(start,cell)&(1<<openSourceSlot))!=0) return vec3(1);
        } else {"""+branch+"\n        }"
        else:
            first=s.index("int torchCellFlags(")
            # The original eligibility routine is required only for comparing the control.
            stop=s.index("// The normal bias",first)
            s=s[:start]+branch+s[end:]
            return s[:first]+s[stop:]
        s=s[:start]+branch+s[end:]
    if diagnostic and name=="shaders/deferred.fsh":
        s=replace(s,"gl_FragData[6]=vec4(probePosition,float(probeNormal));","""
        vec3 inputNormal=areaDecodeNormal(texelFetch(colortex15,pixel,0).w);
        int axisFace=0;
        for(int a=0;a<3;a++) if(abs(inputNormal[a])>.99999) axisFace=1+2*a+int(inputNormal[a]>0.);
        gl_FragData[6]=vec4(probePosition.xy,probePosition.z+128.*float(axisFace),1.);""")
    if diagnostic and name=="shaders/final.fsh":
        s=replace(s,"    vec3 rgb;","    position.w=floor(position.z/128.);position.z=mod(position.z,128.);\n    vec3 rgb;")
    return s

if __name__=="__main__":
    for d,p in ((False,NORMAL),(True,METER)):
        print(p,build(WORK/p,lambda n,s:transform(n,s,d)))
