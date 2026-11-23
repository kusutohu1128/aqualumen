"""Keep a verified cuboid's eclipse when a moving animal also enters the light volume."""
from pack import WORK,NAME,build,replace
from swept import changed
NORMAL=NAME.replace("-Study","-Body")
METER=NAME.replace("-Study","-Body-Meter")

def joint(name,s,diagnostic):
    s=changed(name,s,diagnostic)
    if name!="shaders/lib/local_lighting.glsl":return s
    # Placed torches include the holder's actual body. The carried-light
    # branch continues to integrate all materials and exclude its own holder.
    s=replace(s,"float visible,vec2 witness,inout LampOccluders o)","float visible,vec2 witness,bool carried,inout LampOccluders o)")
    s=replace(s,"        vec3 value=lampSample(start,target,true,o);","""        vec3 value;
#ifdef OPEN_TERRAIN_PATH
        if(!carried) {
            // These rays are already certified clear of all static materials
            // except the cuboid tested above. Use the current mesh and budget.
            value=vec3(1);
#if ENTITY_LIGHT_SHADOWS == 1
            value=vec3(entityTransmission(o.entities,start+o.toRelative,target+o.toRelative,false,o.work));
#endif
        } else
#endif
        value=lampSample(start,target,true,o);""")
    s=replace(s,"lo,hi,area,witness,occluders);","lo,hi,area,witness,true,occluders);")
    start=s.index("float continuousBox(");end=s.index("\n}",start)
    box=s[start:end]
    box=replace(box,"vec3 v,float radius) {","vec3 v,float radius,out vec3 lo,out vec3 hi,out vec2 witness) {\n    witness=vec2(0);")
    box=replace(box,"    vec3 lo=","    lo=")
    box=replace(box,"    vec3 hi=","    hi=")
    box=replace(box,"    vec2 witness;\n","")
    s=s[:start]+box+s[end:]
    s=replace(s,"if(!carried && !occluders.leafVolume && !occluders.entityTest)","if(!carried && !occluders.leafVolume)")
    if diagnostic:s=replace(s,"if((torchCellFlags(start,cell)&(1<<openSourceSlot))!=0)","if(!occluders.entityTest && (torchCellFlags(start,cell)&(1<<openSourceSlot))!=0)")
    s=replace(s,"if((flags&(1<<slot))!=0 && all","if(!occluders.entityTest && (flags&(1<<slot))!=0 && all")
    k="return vec3(continuousBox(cell,slot,start,centre,u,v,radius));"
    start=s.index(k);start=s.rfind("probeMethod=2;",0,start) if diagnostic else start
    end=s.index(k,start)+len(k)
    s=s[:start]+"""vec3 lo,hi; vec2 witness;
                float visible=continuousBox(cell,slot,start,centre,u,v,radius,lo,hi,witness);
                if(!occluders.entityTest || visible<=0.) {
                    METHOD_STATIC
                    return vec3(visible);
                }
                if(visible<1.) {
                    METHOD_BOTH
                    return jointDiskSamples(start,centre,u,v,lo,hi,visible,witness,false,occluders);
                }
                // A fully visible static disk still needs the usual animal shadow.""".replace("METHOD_STATIC","probeMethod=occluders.entityTest?3:2;" if diagnostic else "").replace("METHOD_BOTH","probeMethod=3;" if diagnostic else "")+s[end:]
    return s

if __name__=="__main__":
    for d,p in ((False,NORMAL),(True,METER)):
        print(p,build(WORK/p,lambda n,s:joint(n,s,d)))
