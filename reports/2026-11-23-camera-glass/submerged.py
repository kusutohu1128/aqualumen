"""Measure each side of a real water interface against an independent slab intersection."""
from water_surface import Pool,POSE,HERE,ROOT,STUDY,LAYOUT,meter,ZipFile,zip_bytes,ArchiveEntry,guarded
import sys
LAYOUT["submerged"]={}
class Submerged(Pool):
    def geometry(self,names):
        return dict(super().geometry(names),waterloggedPane={"x":[405,407],"y":151,"z":-410})
    def datapack(self,names):
        files=super().datapack(names)
        i=names.index("submerged")
        k=f"data/animal/function/s{i}.mcfunction"
        marker="say AQLAVA_BEGIN_submerged_END"
        assert files[k].count(marker)==1
        files[k]=files[k].replace(marker,"fill 405 151 -410 407 151 -410 red_stained_glass_pane[waterlogged=true]\n"+marker)
        for phase in "ve":
            k=f"data/animal/function/{phase}{i}.mcfunction"
            old="if block 406 151 -410 water[level=0]"
            assert files[k].count(old)==1
            files[k]=files[k].replace(old,"if block 406 151 -410 red_stained_glass_pane[north=true,south=false,west=true,east=true,waterlogged=true]")
        return files
def instrument():
    with ZipFile(meter(STUDY)) as z:files={k:z.read(k) for k in z.namelist()}
    k="shaders/gbuffers_water.fsh";s=files[k].decode()
    def replace(old,new):
        nonlocal s
        assert s.count(old)==1,old
        s=s.replace(old,new)
    replace("void main() {","""
float testBox(vec3 a,vec3 b,vec3 lo,vec3 hi) {
    vec3 delta=b-a;
    float enter=0., exitAt=1.;
    for(int k=0;k<3;++k) {
        if(abs(delta[k])<1e-7) {
            if(a[k]<lo[k] || a[k]>=hi[k]) return 0.;
        } else {
            vec2 hits=(vec2(lo[k],hi[k])-a[k])/delta[k];
            enter=max(enter,min(hits.x,hits.y));exitAt=min(exitAt,max(hits.x,hits.y));
        }
    }
    return length(delta)*max(exitAt-enter,0.);
}
void main() {""")
    line="    if (receiverKind==1 || (!underwater && !bedFromLight))"
    replace(line,"    behind=vec3(1.);\n"+line)
    replace("gl_FragData[0]=vec4(max(color,vec3(0.0))*paneToEye(worldPosition),1.0);","""
    vec3 a=worldPosition+cameraPosition,b=receiverPoint+cameraPosition;
    float distanceInGlass=testBox(a,b,vec3(405,151,-409.5625),vec3(408,152,-409.4375));
    for(int x=405;x<=407;++x) {
        distanceInGlass+=testBox(a,b,vec3(float(x)+.4375,151,-410),vec3(float(x)+.5625,152,-409.5625));
    }
    gl_FragData[0]=vec4(receiverKind==1?vec3(paneToEye(worldPosition).g,behind.g,pow(.20,distanceInGlass)):vec3(0),1.0);""")
    files[k]=s.encode()
    k="shaders/lib/window_scene.glsl"
    files[k]=files[k].replace(b"color=vec3((int(gl_FragCoord.x)&1)==0?.75:.25);",b"color=vec3(0);")
    data=zip_bytes(tuple(ArchiveEntry(k,v) for k,v in sorted(files.items())))
    pack=ROOT/"build/camera-glass/Aqualumen-Submerged-Glass-Meter.zip"
    if pack.exists() and pack.read_bytes()!=data:raise ValueError("Changed meter")
    pack.write_bytes(data)
    return pack
if __name__=="__main__":
    label=sys.argv[1]
    assert not (HERE/label).exists()
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages="pool,submerged,pool-cleared",glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"210","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(instrument(),label,"off",fixed,HERE,Submerged)
